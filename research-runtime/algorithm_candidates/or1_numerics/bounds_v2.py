"""AL18 bounded interface repair. Original bounds.py remains immutable.

N5 explicit hat_q is validated before unknown-bound exits. N2 explicitly
supports hat_k, validates it first, and passes it to the original N1 engine.
Undeclared top-level output fields are rejected, not silently ignored.
"""
import bounds as v1

SCHEMA={
    'N1':({'hat_ab','hat_ba'},{'hat_ab','hat_ba','hat_k','bounds'}),
    'N2':({'observations'},{'observations','hat_k','bounds'}),
    'N4':({'hat_z'},{'hat_z','hat_n','bounds'}),
    'N5':({'hat_n','hat_d'},{'hat_n','hat_d','hat_q','bounds'})}
OBSERVATIONS={'x','ra0','rb0','pa','pb','rab','rba','uab','uba'}


def n2(payload,h,eta):
    raw=payload['observations']
    if not isinstance(raw,dict) or set(raw)!=OBSERVATIONS:
        raise v1.InvalidInput('N2 observations must have exactly the declared trace fields')
    obs={key:v1.vector(raw[key],key) for key in ('x','ra0','rb0','pa','pb','rab','rba','uab','uba')}
    v1.check_dims(*obs.values())
    supplied=v1.vector(payload['hat_k'],'hat_k') if 'hat_k' in payload else None
    if supplied is not None:v1.check_dims(obs['x'],supplied)
    names=('eps_a0','eps_b0','eps_ab','eps_ba','L_a','L_b','rho_a','rho_b','rho_ab','rho_ba','rho_K')
    b,u,s=v1.parse_bounds(payload.get('bounds',{}),names)
    if u:return v1.unknown_result(u,s)
    for output,left,right,rho in [('pa','x','ra0','rho_a'),('pb','x','rb0','rho_b'),
                                  ('uab','pb','rab','rho_ab'),('uba','pa','rba','rho_ba')]:
        mixed=tuple((1-h)*x+h*y for x,y in zip(obs[left],obs[right]))
        if v1.square_norm(tuple(x-y for x,y in zip(obs[output],mixed)))>b[rho]**2:
            raise v1.InvalidInput(output+': observed mixing error exceeds declared bound')
    ell_a=1-h+h*b['L_a'];ell_b=1-h+h*b['L_b']
    da=h*b['eps_a0']+b['rho_a'];db=h*b['eps_b0']+b['rho_b']
    dab=ell_a*db+h*b['eps_ab']+b['rho_ab'];dba=ell_b*da+h*b['eps_ba']+b['rho_ba']
    result=v1.endpoint_result(obs['uab'],obs['uba'],h,
        dict(delta_ab=dab,delta_ba=dba,rho_K=b['rho_K']),s,hat_k=supplied)
    result['propagation']=dict(ell_a=ell_a,ell_b=ell_b,delta_a=da,delta_b=db,delta_ab=dab,delta_ba=dba)
    result['final_K_observation']='supplied_and_checked' if supplied is not None else 'exactly_recomputed_from_supplied_endpoints'
    return result


def evaluate(kind,payload,h,eta):
    meta=dict(equation=kind,interface_version='AL18-v2',norm='Euclidean, squared energy uses sum',
        arithmetic='exact rational',certificate_scope='conditional on valid declared bounds, not empirical repeat agreement',origin_decision=None)
    try:
        h=v1.rational(h,'h');eta=v1.rational(eta,'eta')
        if not 0<h<=1:raise v1.InvalidInput('Require 0<h<=1')
        if eta<=0:raise v1.InvalidInput('Require eta>0')
        if kind not in SCHEMA:raise v1.InvalidInput('Unknown contract equation')
        if not isinstance(payload,dict):raise v1.InvalidInput('Payload must be a mapping')
        required,allowed=SCHEMA[kind]
        if not required.issubset(payload) or not set(payload).issubset(allowed):
            raise v1.InvalidInput('Missing or unsupported public observation fields')
        if 'bounds' in payload and not isinstance(payload['bounds'],dict):
            raise v1.InvalidInput('Bounds must be an explicit mapping')
        # Public optional observation must be finite even if some error is unknown.
        if kind=='N5' and 'hat_q' in payload:v1.rational(payload['hat_q'],'hat_q')
        result={'N1':v1.n1,'N2':n2,'N4':v1.n4,'N5':v1.n5}[kind](payload,h,eta)
        return meta|dict(h=h,eta=eta)|result
    except v1.InvalidInput as exc:
        return meta|dict(status='invalid_input',interval_valid=False,reason=str(exc))
