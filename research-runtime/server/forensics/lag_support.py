"""Descriptive actual-time support checks; never a trained detector or test gate.

Equal rounded bins do not imply identical continuous timing. Always retain the
raw vectors and report their within-bin class differences. This module cannot
prove a visual classifier uses an available metadata shortcut.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import numpy as np


def timing_vector(sampling: dict, view: str) -> np.ndarray:
    pts = np.asarray(sampling['pts'], dtype=np.float64)
    if pts.shape != (8,) or not np.isfinite(pts).all() or not (np.diff(pts) > 0).all():
        raise ValueError('Expected eight finite, strictly increasing native-frame timestamps')
    if view == 'all_adjacent':
        return np.diff(pts)
    if view == 'half_second':
        return np.asarray([pts[4] - pts[0]])
    raise ValueError('Unknown timing view: ' + view)


def quantized_signature(values: np.ndarray, quantum: float) -> tuple[int, ...]:
    values = np.asarray(values, dtype=np.float64)
    if not np.isfinite(quantum) or quantum <= 0 or not np.isfinite(values).all():
        raise ValueError('Quantization requires finite data and positive quantum')
    if np.max(np.abs(values), initial=0) / quantum > 2**52:
        raise ValueError('Timing/quantum exceeds exact integer resolution')
    return tuple(np.floor(values / quantum + .5).astype(np.int64).tolist())


def support_report(rows: list[dict], view: str, quantum: float,
                   target_lag: float = .5, tolerance: float = .002) -> tuple[dict, list[dict]]:
    """Audit support on a supplied descriptive cohort; use no classifier scores.

    `rows` must have sample_id, source, label_fake, group, sampling. Half-second
    admission tests the observed lag against an absolute tolerance, independent
    of class. Labels are used only to describe overlap, never to pick a frame.
    """
    if tolerance < 0 or not np.isfinite(tolerance) or not np.isfinite(target_lag):
        raise ValueError('Invalid lag target/tolerance')
    if len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate sample IDs in support audit')
    sources = sorted({r['source'] for r in rows})
    classes = defaultdict(set)
    bins = defaultdict(list)
    annotated = []
    for row in rows:
        if row['label_fake'] not in (0, 1):
            raise ValueError('Binary labels required')
        if 'final' in row.get('role', '').lower():
            raise ValueError('This descriptive audit must not open a final cohort')
        values = timing_vector(row['sampling'], view)
        admitted = view != 'half_second' or abs(values[0] - target_lag) <= tolerance + 1e-12
        key = quantized_signature(values, quantum)
        item = dict(sample_id=row['sample_id'], source=row['source'], label_fake=row['label_fake'],
                    group=row['group'], actual_timing=values.tolist(), signature=list(key),
                    lag_eligible=bool(admitted))
        classes[row['source']].add(row['label_fake'])
        annotated.append(item)
        if admitted:
            bins[key].append(item)
    total = Counter(r['source'] for r in annotated)
    eligible = Counter(r['source'] for r in annotated if r['lag_eligible'])
    by_source = {source: Counter({key: sum(r['source'] == source for r in members)
                                 for key, members in bins.items()}) for source in sources}
    pairs = []
    for real in sources:
        if classes[real] != {0}:
            continue
        for fake in sources:
            if classes[fake] != {1}:
                continue
            common = [key for key in bins if by_source[real][key] and by_source[fake][key]]
            nr, nf = eligible[real], eligible[fake]
            overlap = (sum(min(by_source[real][key] / nr, by_source[fake][key] / nf)
                           for key in common) if nr and nf else None)
            groups = {s: set() for s in (real, fake)}
            raw_differences = []
            for key in common:
                vectors = {s: np.array([r['actual_timing'] for r in bins[key] if r['source'] == s]) for s in (real, fake)}
                raw_differences.append(float(np.max(np.abs(vectors[real].mean(0) - vectors[fake].mean(0)))))
                for r in bins[key]:
                    if r['source'] in groups:
                        groups[r['source']].add(r['group'])
            pairs.append(dict(real_source=real, fake_source=fake, common_bins=len(common),
                eligible_counts={real:nr, fake:nf},
                supported_counts={s:sum(by_source[s][key] for key in common) for s in (real,fake)},
                supported_groups={s:len(groups[s]) for s in (real,fake)},
                discrete_overlap_coefficient=overlap,
                largest_within_bin_mean_timing_difference=max(raw_differences,default=None)))
    all_source_bins = [key for key in bins if all(by_source[s][key] for s in sources)]
    mixed_class_bins = {key for key, members in bins.items() if {r['label_fake'] for r in members} == {0,1}}
    for r in annotated:
        key = tuple(r['signature'])
        r['mixed_class_support'] = bool(r['lag_eligible'] and key in mixed_class_bins)
        r['all_source_support'] = bool(r['lag_eligible'] and key in all_source_bins)
    summary = dict(view=view, quantum_seconds=quantum, target_lag_seconds=target_lag if view=='half_second' else None,
        tolerance_seconds=tolerance if view=='half_second' else None, counts=dict(total),
        lag_eligible_counts={s:eligible[s] for s in sources}, bins=len(bins), mixed_class_bins=len(mixed_class_bins),
        all_source_common_bins=len(all_source_bins),
        all_source_supported_counts={s:sum(by_source[s][key] for key in all_source_bins) for s in sources},
        real_fake_source_pairs=pairs, classifier_scores_used=False,
        interpretation='Descriptive overlap of observed timing only. Quantization is not timing removal; no detector or causal claim.')
    return summary, annotated
