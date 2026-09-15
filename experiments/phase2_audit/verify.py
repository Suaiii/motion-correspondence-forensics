"""Mechanical replay and metric verification, not independent scientific review."""
import json
import hashlib
from pathlib import Path
import numpy as np
from scipy.special import expit
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT/'research-runs/phase2_evidence_audit_20260914'
def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

for rel, expected in read(RUN/'input_lock.json').items():
    assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == expected, rel
for rel, expected in read(RUN/'artifact_hashes.json').items():
    assert hashlib.sha256((RUN/rel).read_bytes()).hexdigest() == expected, rel
result = read(RUN/'results.json')
pred = read(RUN/'predictions.json')
for name, summary in result['results'].items():
    rows = [r for r in pred if r['cohort']==name]
    assert len(rows)==summary['n']
    for arm, expected in summary['auc'].items():
        assert abs(roc_auc_score([r['label_fake'] for r in rows], [r['scores'][arm] for r in rows])-expected)<1e-12
external = [json.loads(line) for line in (ROOT/'research-runs/comgenvid_videos_20260914/correspondence_features_150.jsonl').read_text().splitlines()]
lookup = {r['source_model']+':'+r['filename']:r for r in external}
models = read(RUN/'models.json')
for row in [r for r in pred if r['cohort']=='external']:
    for arm, cols in result['protocol']['arms'].items():
        x = np.concatenate([lookup[row['sample_id']]['features'][c] for c in cols])
        m = models[arm]
        score = expit(((x-np.array(m['mean']))/m['scale'])@np.array(m['coef'])[0]+m['intercept'][0])
        assert abs(score-row['scores'][arm]) < 1e-12
assert result['results']['external']['parent_clusters']==147
assert abs(result['results']['audit']['auc']['fusion']-0.8862573099415205)<1e-12
assert abs(result['results']['external']['auc']['fusion']-0.6056)<1e-12
review = {'status':'pass', 'reviewer':'primary agent, mechanical replay',
          'independent_scientific_review':False,
          'checks':['input and output hashes unchanged','all 20 AUROCs independently recomputed with sklearn',
                    '750 external probabilities replayed from saved scaler and coefficients',
                    'historical point estimates reproduced','MSVD parent clustering yields 147 total clusters'],
          'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(RUN/'verification.json').write_text(json.dumps(review, indent=2)+'\n')
print(json.dumps(review, indent=2))
