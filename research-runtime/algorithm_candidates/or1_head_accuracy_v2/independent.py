"""Separate stdlib rational and scalar checks, never imports vector objective."""
from fractions import Fraction as F
import math


def rank(rows):
    a = [list(row) for row in rows]
    r = 0
    for c in range(len(a[0])):
        pivot = next((i for i in range(r, len(a)) if a[i][c]), None)
        if pivot is None:
            continue
        a[r], a[pivot] = a[pivot], a[r]
        scale = a[r][c]
        a[r] = [v / scale for v in a[r]]
        for i in range(len(a)):
            if i != r:
                scale = a[i][c]
                a[i] = [v - scale * u for v, u in zip(a[i], a[r])]
        r += 1
        if r == len(a):
            break
    return r


def exact_panel(panel, transform):
    plus = [[F(x) for x in row] for row in panel['plus']]
    minus = [[F(x) for x in row] for row in panel['minus']]
    dz = [[a - b for a, b in zip(p, m)] for p, m in zip(plus, minus)]
    dq = [[sum(row[k] * transform[k][j] for k in range(12)) for j in range(4)] for row in dz]
    gram = []
    for side, rows in [('plus', plus), ('minus', minus)]:
        for i, row in enumerate(rows):
            for block in range(4):
                a, b, c = row[3*block:3*block+3]
                gram.append(dict(side=side, row=i, block=block, a=str(a), b=str(b), c=str(c),
                                 determinant=str(a*b-c*c), feasible=a >= 0 and b >= 0 and a*b >= c*c))
    gradients = {}
    for name, rows in [('candidate', dq), ('free', dz)]:
        gradients[name] = [str(-sum(row[j] for row in rows) / (2 * len(rows))) for j in range(len(rows[0]))]
    return dict(rank_z=rank(dz), rank_q=rank(dq), gradient_at_zero=gradients,
                gram_checks=gram, gram_feasible=all(g['feasible'] for g in gram),
                dz=[[str(v) for v in row] for row in dz], dq=[[str(v) for v in row] for row in dq])


def scalar_reference(panel, config):
    if panel == 'aligned':
        margin_scale, norm_coefficient = 0.75, 0.004
    elif panel in ['full_rank', 'full_rank_scale']:
        margin_scale = 0.25 if panel == 'full_rank' else 0.125
        norm_coefficient = 0.002
    else:
        raise ValueError(panel)
    calls = []
    def derivative(x):
        value = -margin_scale / (1 + math.exp(margin_scale*x)) + 2*norm_coefficient*x
        calls.append(dict(x=x, derivative=value))
        return value
    lo, hi = config['bracket']
    assert derivative(lo) < 0 < derivative(hi)
    iterations = 0
    while hi - lo > config['width_tolerance'] and iterations < config['max_iterations']:
        mid = (lo + hi) / 2
        if derivative(mid) < 0:
            lo = mid
        else:
            hi = mid
        iterations += 1
    root = (lo + hi) / 2
    residual = derivative(root)
    objective = math.log1p(math.exp(-margin_scale*root)) + norm_coefficient*root*root
    return dict(root=root, bracket=[lo, hi], iterations=iterations, derivative=residual,
                objective=objective, evaluations=calls,
                status='width_tolerance' if hi-lo <= config['width_tolerance'] else 'maximum_iterations',
                rigorous_certificate=False)
