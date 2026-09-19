"""Exact finite population controls; no model or statistical sample fitting."""
from fractions import Fraction as F


def validate_vector(values, length, probability=False):
    if len(values) != length or any(not isinstance(v, F) for v in values):
        raise ValueError('Expected a fixed-length Fraction vector')
    if any(v < 0 or (probability and v > 1) for v in values):
        raise ValueError('Invalid mass or selection probability')


def normalize(masses):
    total = sum(masses, F(0))
    if total <= 0:
        raise ValueError('Empty selected population')
    return tuple(p / total for p in masses)


def selected_law(base, selection):
    validate_vector(base, len(base), probability=True)
    validate_vector(selection, len(base), probability=True)
    if sum(base, F(0)) != 1:
        raise ValueError('Base law is not normalized')
    mass = tuple(p * s for p, s in zip(base, selection))
    return sum(mass, F(0)), mass, normalize(mass)


def auc(law0, law1, scores):
    if not (len(law0) == len(law1) == len(scores)):
        raise ValueError('Mismatched supports')
    total = F(0)
    for i, p1 in enumerate(law1):
        for j, p0 in enumerate(law0):
            total += p1 * p0 * (1 if scores[i] > scores[j] else F(1, 2) if scores[i] == scores[j] else 0)
    return total


def marginal_z(cells, law):
    return {z: sum((p for (zi, _), p in zip(cells, law) if zi == z), F(0))
            for z in sorted({z for z, _ in cells})}


def match_z(cells, law0, law1):
    m0, m1 = marginal_z(cells, law0), marginal_z(cells, law1)
    common = [z for z in m0 if m0[z] > 0 and m1[z] > 0]
    overlap = sum((min(m0[z], m1[z]) for z in common), F(0))
    if overlap == 0:
        return {'status': 'no_common_support', 'matched0': None, 'matched1': None}
    target = {z: min(m0[z], m1[z]) / overlap for z in common}
    def remap(law, marginal):
        return tuple(target[z] * p / marginal[z] if z in target else F(0)
                     for (z, _), p in zip(cells, law))
    gaps = {}
    for z in common:
        pq0 = sum((p for (zi, q), p in zip(cells, law0) if zi == z and q == 1), F(0)) / m0[z]
        pq1 = sum((p for (zi, q), p in zip(cells, law1) if zi == z and q == 1), F(0)) / m1[z]
        gaps[z] = pq1 - pq0
    return {'status': 'conditional_common_support_only', 'marginal0': m0, 'marginal1': m1,
            'overlap_mass': overlap, 'common_Z': common, 'target_Z': target,
            'outside0': sum((v for z, v in m0.items() if z not in common), F(0)),
            'outside1': sum((v for z, v in m1.items() if z not in common), F(0)),
            'matched0': remap(law0, m0), 'matched1': remap(law1, m1),
            'conditional_Q1_gap': gaps}


def inverse_probability(law, selection, cells):
    missing = [cell for cell, s in zip(cells, selection) if s == 0]
    if missing:
        return {'status': 'full_population_unidentifiable_zero_propensity',
                'unobserved_cells': missing, 'recovered_law': None}
    return {'status': 'recovered_with_oracle_positive_propensity',
            'unobserved_cells': [], 'recovered_law': normalize(tuple(p / s for p, s in zip(law, selection)))}
