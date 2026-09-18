"""Independent stdlib Fraction linear-coordinate and archived-array arithmetic."""
from fractions import Fraction as F


def transpose(a):
    return [list(row) for row in zip(*a)]


def multiply(a,b):
    return [[sum(x*y for x,y in zip(row,col)) for col in zip(*b)] for row in a]


def vector(a,x):
    return [sum(v*w for v,w in zip(row,x)) for row in a]


def flat(x):
    if isinstance(x,list):
        return [v for item in x for v in flat(item)]
    return [F.from_float(x)]


def strings(x):
    return [strings(v) if isinstance(v,list) else str(v) for v in x]


def field_reference(record):
    a,b,k = [flat(record['filtered_fields'][key]) for key in ['d_a','d_b','K']]
    s = [x+y for x,y in zip(a,b)]
    d = F.from_float(record['D'])
    rs = sum(v*v for v in s)/len(s)/d
    rj = sum(v*w for v,w in zip(s,k))/len(s)/d
    # K energy is deliberately not recomputed. This reference also reuses stored q.
    return [rs,F.from_float(record['q_direct']),rj]


def panel_reference(panel,block,points,coefficient):
    plus=[[F(v) for v in row] for row in panel['plus']]
    minus=[[F(v) for v in row] for row in panel['minus']]
    rplus=[vector(block,row) for row in plus]
    rminus=[vector(block,row) for row in minus]
    dz=[[a-b for a,b in zip(p,m)] for p,m in zip(plus,minus)]
    dr=[[a-b for a,b in zip(p,m)] for p,m in zip(rplus,rminus)]
    transformed=[vector(block,row) for row in dz]
    metric=multiply(block,transpose(block))
    result=dict(plus_r=strings(rplus),minus_r=strings(rminus),delta_z=strings(dz),
                delta_r=strings(dr),difference_transform_exact=dr==transformed,points=[])
    for point in points:
        gamma=[F(v) for v in point['gamma']]
        beta=vector(transpose(block),gamma)
        zmargins=vector(dz,beta)
        rmargins=vector(dr,gamma)
        penalty_beta=coefficient*sum(v*v for v in beta)
        penalty_gamma=coefficient*sum(v*w for v,w in zip(gamma,vector(metric,gamma)))
        result['points'].append(dict(name=point['name'],gamma=strings(gamma),beta=strings(beta),
            margins_beta=strings(zmargins),margins_gamma=strings(rmargins),
            penalty_beta=str(penalty_beta),penalty_gamma=str(penalty_gamma),
            exact_equal=zmargins==rmargins and penalty_beta==penalty_gamma))
    return result
