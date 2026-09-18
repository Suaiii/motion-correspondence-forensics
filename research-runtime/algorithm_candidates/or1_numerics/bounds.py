"""AL18 exact conditional numerical contracts. Standard library only.

No inferred AE error bounds: every bound requires an explicit declared basis.
All safety arithmetic uses Fraction; optional float values are display-only.
"""
from fractions import Fraction as F
from math import isfinite,isqrt

class InvalidInput(ValueError):
    pass


def rational(value,name):
    if isinstance(value,bool) or value is None:
        raise InvalidInput(name+': finite real number required')
    if isinstance(value,F):return value
    if isinstance(value,int):return F(value)
    if isinstance(value,float):
        if not isfinite(value):raise InvalidInput(name+': nonfinite value')
        return F.from_float(value)
    if isinstance(value,str):
        try:return F(value)
        except (ValueError,ZeroDivisionError,OverflowError) as exc:
            raise InvalidInput(name+': invalid rational/nonfinite text') from exc
    raise InvalidInput(name+': unsupported numeric type')


def vector(value,name):
    if not isinstance(value,(list,tuple)) or not 1<=len(value)<=8:
        raise InvalidInput(name+': vector length 1..8 required')
    return tuple(rational(v,f'{name}[{i}]') for i,v in enumerate(value))


def square_norm(v):return sum((x*x for x in v),F(0))


def sqrt_enclosure(q,bits=60):
    """Rational enclosure of the Euclidean norm, checked by exact squaring."""
    if q<0:raise InvalidInput('Squared norm is negative')
    a,b=isqrt(q.numerator),isqrt(q.denominator)
    if a*a==q.numerator and b*b==q.denominator:
        value=F(a,b);return value,value,True
    scale=1<<bits
    floor=isqrt((q.numerator*scale*scale)//q.denominator)
    lo,hi=F(floor,scale),F(floor+1,scale)
    if not lo*lo<=q<=hi*hi:raise ArithmeticError('Rational sqrt enclosure failed')
    return lo,hi,False


def norm_enclosure(v):return sqrt_enclosure(square_norm(v))


def parse_bounds(raw,names):
    known={};unknown=[];sources={}
    for name in names:
        entry=raw.get(name)
        if entry is None:
            unknown.append(dict(field=name,reason='missing_or_unknown'));continue
        if not isinstance(entry,dict):raise InvalidInput(name+': bound value and basis required')
        value=entry.get('value');basis=entry.get('basis','unknown');sources[name]=basis
        if value is not None:
            value=rational(value,name)
            if value<0:raise InvalidInput(name+': negative bound')
        if value is None or basis not in ('analytic_mock','exact_rational_arithmetic','declared_valid_assumption'):
            unknown.append(dict(field=name,reason='unknown_or_not_a_valid_bound',basis=basis))
        else:known[name]=value
    return known,unknown,sources


def unknown_result(unknown,sources):
    return dict(status='uncertified_bound',interval_valid=False,unknown_fields=unknown,bound_sources=sources,
        reason='Unknown or empirical-only errors/Lipschitz values are never filled with zero')


def check_dims(*vectors):
    if len({len(v) for v in vectors})!=1:raise InvalidInput('Vector dimensions differ')


def endpoint_result(ab,ba,h,bounds,sources,hat_k=None):
    check_dims(ab,ba)
    exact_from_observed=tuple((a-b)/(h*h) for a,b in zip(ab,ba))
    observed=exact_from_observed if hat_k is None else hat_k
    check_dims(ab,observed)
    if square_norm(tuple(x-y for x,y in zip(observed,exact_from_observed)))>bounds['rho_K']**2:
        raise InvalidInput('Observed final arithmetic error exceeds declared rho_K')
    bk=(bounds['delta_ab']+bounds['delta_ba'])/(h*h)+bounds['rho_K']
    lo_norm,hi_norm,exact=norm_enclosure(observed)
    lower=max(F(0),lo_norm-bk)
    return dict(status='conditional_interval' if lower>0 else 'residual_energy_not_certified_positive',
        interval_valid=True,K_hat=observed,B_K=bk,
        coordinate_intervals=[(x-bk,x+bk) for x in observed],
        observed_norm_enclosure=(lo_norm,hi_norm),norm_enclosure_exact=exact,
        response_norm_lower=lower,response_energy_lower=lower*lower,
        energy_positive_certified=lower>0,bound_sources=sources,
        interpretation='Euclidean error ball and coordinate enclosure, conditional on declared endpoint bounds')


def n1(payload,h,eta):
    ab=vector(payload['hat_ab'],'hat_ab');ba=vector(payload['hat_ba'],'hat_ba');check_dims(ab,ba)
    hat_k=vector(payload['hat_k'],'hat_k') if 'hat_k' in payload else None
    b,u,s=parse_bounds(payload.get('bounds',{}),('delta_ab','delta_ba','rho_K'))
    if u:return unknown_result(u,s)
    return endpoint_result(ab,ba,h,b,s,hat_k)


def n2(payload,h,eta):
    obs={key:vector(payload['observations'][key],key) for key in ('x','ra0','rb0','pa','pb','rab','rba','uab','uba')}
    check_dims(*obs.values())
    names=('eps_a0','eps_b0','eps_ab','eps_ba','L_a','L_b','rho_a','rho_b','rho_ab','rho_ba','rho_K')
    b,u,s=parse_bounds(payload.get('bounds',{}),names)
    if u:return unknown_result(u,s)
    for output,left,right,rho in [('pa','x','ra0','rho_a'),('pb','x','rb0','rho_b'),
                                  ('uab','pb','rab','rho_ab'),('uba','pa','rba','rho_ba')]:
        mixed=tuple((1-h)*x+h*y for x,y in zip(obs[left],obs[right]))
        if square_norm(tuple(x-y for x,y in zip(obs[output],mixed)))>b[rho]**2:
            raise InvalidInput(output+': observed mixing error exceeds declared bound')
    ell_a=1-h+h*b['L_a'];ell_b=1-h+h*b['L_b']
    da=h*b['eps_a0']+b['rho_a'];db=h*b['eps_b0']+b['rho_b']
    dab=ell_a*db+h*b['eps_ab']+b['rho_ab'];dba=ell_b*da+h*b['eps_ba']+b['rho_ba']
    result=endpoint_result(obs['uab'],obs['uba'],h,dict(delta_ab=dab,delta_ba=dba,rho_K=b['rho_K']),s)
    result['propagation']=dict(ell_a=ell_a,ell_b=ell_b,delta_a=da,delta_b=db,delta_ab=dab,delta_ba=dba)
    return result


def n4(payload,h,eta):
    z=vector(payload['hat_z'],'hat_z');energy=square_norm(z)
    hat_n=rational(payload.get('hat_n',energy),'hat_n')
    if hat_n<0:raise InvalidInput('Observed energy must be nonnegative')
    b,u,s=parse_bounds(payload.get('bounds',{}),('B_z','rho_N'))
    if u:return unknown_result(u,s)
    if abs(hat_n-energy)>b['rho_N']:raise InvalidInput('Observed energy arithmetic exceeds rho_N')
    lo,upper,exact=norm_enclosure(z)
    bn=2*upper*b['B_z']+b['B_z']**2+b['rho_N']
    low=max(F(0),hat_n-bn)
    return dict(status='conditional_interval' if low>0 else 'residual_energy_not_certified_positive',
        interval_valid=True,hat_n=hat_n,B_N=bn,numerator_interval=(low,hat_n+bn),
        observed_norm_enclosure=(lo,upper),norm_enclosure_exact=exact,
        energy_positive_certified=low>0,bound_sources=s,
        interpretation='N4 uses an exact or rational-upper Euclidean norm; no float rounding is used as a proof')


def linear_score(q_hat,b_q,weights,rho_s,threshold=F(0)):
    if len(q_hat)!=len(b_q) or len(q_hat)!=len(weights):raise InvalidInput('Score dimensions differ')
    q_hat=[rational(x,'q_hat') for x in q_hat];b_q=[rational(x,'B_q') for x in b_q]
    if any(x<0 for x in b_q):raise InvalidInput('Negative ratio bound')
    w=[rational(x,'weight') for x in weights];rho_s=rational(rho_s,'rho_s');threshold=rational(threshold,'threshold')
    if rho_s<0:raise InvalidInput('Negative score arithmetic bound')
    score=sum((a*b for a,b in zip(w,q_hat)),F(0))
    error=sum((abs(a)*b for a,b in zip(w,b_q)),F(0))+rho_s
    interval=(score-error,score+error)
    sign='strict_positive' if interval[0]>threshold else 'strict_negative' if interval[1]<threshold else 'boundary_or_uncertain'
    return dict(score_hat=score,B_score=error,interval=interval,threshold=threshold,sign_stability=sign,
        origin_decision=None,scope='Numerical sign stability only; no correctness of source classification claimed')


def n5(payload,h,eta):
    hn=rational(payload['hat_n'],'hat_n');hd=rational(payload['hat_d'],'hat_d')
    if hn<0 or hd<0:raise InvalidInput('Observed energy/denominator must be nonnegative')
    b,u,s=parse_bounds(payload.get('bounds',{}),('B_N','B_D','rho_q','rho_s'))
    if u:return unknown_result(u,s)
    lower_d=hd-b['B_D'];lower_n=max(F(0),hn-b['B_N'])
    if lower_d<=0:
        return dict(status='denominator_lower_not_positive',interval_valid=False,denominator_lower=lower_d,
            numerator_energy_lower=lower_n,bound_sources=s,
            reason='AL16 N5 lower-bound test fails; structural d>=eta is not used to bypass this stability gate')
    exact_division=hn/hd
    qhat=rational(payload.get('hat_q',exact_division),'hat_q')
    if abs(qhat-exact_division)>b['rho_q']:
        raise InvalidInput('Observed quotient arithmetic exceeds rho_q')
    bq=b['B_N']/lower_d+abs(hn)*b['B_D']/(hd*lower_d)+b['rho_q']
    lower_residual=max(F(0),lower_d-eta)
    reasons=[]
    if lower_n<=0:reasons.append('response_energy_not_certified_positive')
    if lower_residual<=0:reasons.append('denominator_residual_energy_not_certified_positive')
    return dict(status='residual_energy_not_certified_positive' if reasons else 'conditional_interval',
        interval_valid=True,q_hat=qhat,B_q=bq,ratio_interval=(max(F(0),qhat-bq),qhat+bq),
        denominator_lower=lower_d,numerator_energy_lower=lower_n,
        denominator_residual_energy_lower=lower_residual,nonpositivity_reasons=reasons,
        score=linear_score([qhat],[bq],[F(1)],b['rho_s'],F(0)),bound_sources=s,
        interpretation='Interval may be valid while positive residual energy remains unproved; neither state is an origin label')


def evaluate(kind,payload,h,eta):
    meta=dict(equation=kind,norm='Euclidean, squared energy uses sum',arithmetic='exact rational',
        certificate_scope='conditional on valid declared bounds, not empirical repeat agreement',origin_decision=None)
    try:
        h=rational(h,'h');eta=rational(eta,'eta')
        if not 0<h<=1:raise InvalidInput('Require 0<h<=1')
        if eta<=0:raise InvalidInput('Require eta>0')
        if kind not in ('N1','N2','N4','N5'):raise InvalidInput('Unknown contract equation')
        result={'N1':n1,'N2':n2,'N4':n4,'N5':n5}[kind](payload,h,eta)
        return meta|dict(h=h,eta=eta)|result
    except InvalidInput as exc:
        return meta|dict(status='invalid_input',interval_valid=False,reason=str(exc))
