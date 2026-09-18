"""Exact exhaustive reference for at most four points per bipartition."""
from fractions import Fraction as F
import math
import sys

class MatchingInputError(ValueError):pass


def rational(x):
    if isinstance(x,bool) or x is None:raise MatchingInputError('Finite standardized coordinate required')
    if isinstance(x,float):
        if not math.isfinite(x):raise MatchingInputError('Nonfinite standardized b')
        return F.from_float(x)
    try:return F(x)
    except (ValueError,TypeError,ZeroDivisionError,OverflowError) as exc:
        raise MatchingInputError('Invalid standardized coordinate') from exc


def points(values):
    if not isinstance(values,(list,tuple)) or len(values)>4:
        raise MatchingInputError('Hard limit: at most four items on each side')
    out=[]
    for row in values:
        if set(row)!={'id','b'}:raise MatchingInputError('Matcher accepts id/b only; no q-dependent selection')
        if not isinstance(row['id'],str) or not row['id']:raise MatchingInputError('Nonempty string ID required')
        if len(row['b'])!=12:raise MatchingInputError('Already-standardized b must have 12 coordinates')
        out.append((row['id'],tuple(rational(x) for x in row['b'])))
    return sorted(out,key=lambda x:x[0])


def exact_match(left,right,caliper=F(1,2)):
    if caliper!=F(1,2):raise MatchingInputError('Frozen RMS caliper is 1/2')
    p=points(left);n=points(right)
    container_bytes=max((sys.getsizeof(v)+sum(sys.getsizeof(x)+sys.getsizeof(x.numerator)+sys.getsizeof(x.denominator) for x in v) for _,v in p+n),default=0)
    if container_bytes>1048576:raise MatchingInputError('Numeric descriptor container exceeds 1 MiB')
    identifiers=[x[0] for x in p+n]
    if len(set(identifiers))!=len(identifiers):raise MatchingInputError('Duplicate IDs')
    edges={};all_costs=[]
    for pid,pb in p:
        for nid,nb in n:
            cost=sum(((x-y)**2 for x,y in zip(pb,nb)),F(0))/12
            allowed=cost<=caliper**2
            all_costs.append(dict(pair=(pid,nid),squared_RMS_cost=cost,admissible=allowed))
            if allowed:edges[(pid,nid)]=cost
    feasible=[]
    def enumerate_matches(i,used,pairs,cost):
        if i==len(p):
            feasible.append(dict(pairs=tuple(pairs),cardinality=len(pairs),cost=cost));return
        pid=p[i][0]
        enumerate_matches(i+1,used,pairs,cost)
        for nid,_ in n:
            if nid not in used and (pid,nid) in edges:
                enumerate_matches(i+1,used|{nid},pairs+[(pid,nid)],cost+edges[(pid,nid)])
    enumerate_matches(0,set(),[],F(0))
    maximum=max(r['cardinality'] for r in feasible)
    minimum=min(r['cost'] for r in feasible if r['cardinality']==maximum)
    tied=sorted(r['pairs'] for r in feasible if r['cardinality']==maximum and r['cost']==minimum)
    selected=tied[0]
    return dict(status='supported_matching' if maximum else 'no_training_support',
        selected_pairs=selected,cardinality=maximum,total_squared_RMS_cost=minimum,
        all_max_cardinality_min_cost_ties=tied,admissible_edges=[pair for pair in sorted(edges)],
        all_pair_costs=all_costs,feasible_matchings_enumerated=feasible,
        unmatched_left=[pid for pid,_ in p if pid not in {a for a,b in selected}],
        unmatched_right=[nid for nid,_ in n if nid not in {b for a,b in selected}],
        selection_rule='maximum cardinality, minimum exact squared-RMS cost, then sorted pair-ID list lexical order',
        standardization_performed=False,q_accessed=False,max_descriptor_container_bytes=container_bytes,
        scalability='exhaustive small reference only; maximum 4 per side')
