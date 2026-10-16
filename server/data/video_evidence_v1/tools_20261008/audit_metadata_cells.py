"""Describe visible metadata confounds without fitting or evaluating a detector."""
import collections
from fractions import Fraction
import json
from pathlib import Path
import statistics


def main():
    root=Path('/srv/video_evidence_v1').resolve()
    cells=collections.defaultdict(list)
    with (root/'v1_manifest.jsonl').open() as f:
        for line in f:
            row=json.loads(line)
            p=row['ffprobe']
            pts=p['pts']
            cells[(row['package'],row['variant'],row['label'],row['generator'])].append({
                'codec':p['codec_name'],'width':p['width'],'height':p['height'],
                'fps':float(Fraction(p['avg_frame_rate'])),
                'native_pts_span_seconds':float(Fraction(pts[-1]-pts[0])*Fraction(p['time_base'])),
                'native_frame_count':len(pts)})
    records=[]
    for key, rows in sorted(cells.items()):
        cell=dict(zip(('package','variant','label','generator'),key))
        cell['count']=len(rows)
        cell['codecs']=dict(collections.Counter(r['codec'] for r in rows))
        cell['resolutions']=dict(collections.Counter(str(r['width'])+'x'+str(r['height']) for r in rows))
        for field in ('fps','native_pts_span_seconds','native_frame_count'):
            values=[r[field] for r in rows]
            cell[field]={'min':min(values),'median':statistics.median(values),'max':max(values)}
        records.append(cell)
    result={'scope':'descriptive metadata support; no model score or mechanism conclusion',
        'physical_duration_definition':'last native PTS minus first native PTS, multiplied by rational time_base; excludes final frame display duration',
        'cells':records}
    (root/'operational_20261008/metadata_cells.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([r for r in records if r['variant']=='clean' and r['package']=='AAGenvid_RoboVidSM_v02']))


if __name__=='__main__':
    main()
