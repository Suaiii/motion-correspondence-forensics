"""AL15 OR1 vector core; NumPy/stdlib only, no media/filter/model implementation."""
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_key]='2'
from dataclasses import dataclass
import copy
import math
import numpy as np

MAX_BYTES=1048576
MAX_DIM=8
MAX_OBSERVED_ARRAY_BYTES=0

class ContractError(ValueError):
    pass


def track(x):
    global MAX_OBSERVED_ARRAY_BYTES
    MAX_OBSERVED_ARRAY_BYTES=max(MAX_OBSERVED_ARRAY_BYTES,x.nbytes)
    if x.nbytes>MAX_BYTES:raise ContractError('Task array exceeds 1 MiB')
    return x


def vector(x):
    if np.iscomplexobj(x):raise ContractError('Real vector required')
    value=track(np.asarray(x,dtype=np.float64))
    if value.ndim!=1 or not 1<=len(value)<=MAX_DIM or not np.isfinite(value).all():
        raise ContractError('Finite vector of dimension 1..8 required')
    return value


def scalar(x,name):
    if isinstance(x,(bool,np.bool_,str,bytes)) or np.iscomplexobj(x) or np.ndim(x)!=0:
        raise ContractError(name+' must be a real numeric scalar')
    if np.asarray(x).dtype.kind not in 'iuf':raise ContractError(name+' numeric dtype required')
    value=float(x)
    if not math.isfinite(value) or value<=0:raise ContractError(name+' must be positive and finite')
    return value


def validate_support(support,n):
    required={'slot_ids','window','clock_policy','condition_id','intermediate_lossy_codec','cache_policy'}
    if set(support)!=required:raise ContractError('Unexpected/missing support or forbidden inference metadata')
    if len(support['slot_ids'])!=n or len(set(support['slot_ids']))!=n:
        raise ContractError('Unique declared coordinate slots required')
    if support['window']!=[0,1] or support['clock_policy']!='mock_declared_grid':
        raise ContractError('Undeclared mock window/clock')
    if support['condition_id']!='mock_none':raise ContractError('Undeclared condition')
    if support['intermediate_lossy_codec'] is not False:raise ContractError('No intermediate lossy codec')
    if support['cache_policy']!='fresh_empty_per_call':raise ContractError('Independent initial caches required')


@dataclass
class ProbeResult:
    value: np.ndarray
    support: dict


class MockProbe:
    """Closed mock operator. Private invocation counter is diagnostic only.

    Every allowed normal output depends on vector and frozen parameters, never
    producer identity, source labels or hidden latents. No random generator used.
    """
    def __init__(self,spec):
        self.spec=copy.deepcopy(spec)
        self.name=spec['name']
        self.deterministic=spec.get('deterministic',True)
        self.invocations=0

    def run(self,x,cache,support):
        self.invocations+=1
        if cache!={'history':[]}:
            raise ContractError('Mock received a nonempty initial cache')
        kind=self.spec['kind']
        if kind=='linear':
            a=track(np.asarray(self.spec['matrix'],dtype=np.float64))
            if a.shape!=(len(x),len(x)):raise ContractError('Matrix/vector shape mismatch')
            y=track(a@x)
        elif kind=='translation':
            y=track(x+track(np.asarray(self.spec['offset'],dtype=np.float64)))
        elif kind in ('nonlinear_a','nonlinear_b'):
            y=track(x.copy());i,j=self.spec['active_slots']
            if kind=='nonlinear_a':y[j]+=x[i]**2
            else:y[i]+=x[j]
        else:raise ContractError('Unknown mock operator')
        cache['history'].append('one_mock_call')
        out_support=copy.deepcopy(support)
        behavior=self.spec.get('behavior','normal')
        if behavior=='nan_output':y[0]=np.nan
        elif behavior=='slot_mismatch':out_support['slot_ids'][0]='unexpected_slot'
        elif behavior=='window_mismatch':out_support['window']=[0,2]
        elif behavior=='shape_mismatch':y=track(y[:-1])
        elif behavior=='alternating':y=track(y+(self.invocations%2)*0.125)
        return ProbeResult(y,out_support)


class Ledger:
    def __init__(self):
        self.records=[]
        # Retain cache objects to verify identities, not merely re-used id ints.
        self.caches=[]

    def call(self,probe,x,support,*,purpose,evaluation_id,node,parent,soft_step=None):
        cache={'history':[]}
        unique=all(cache is not other for other in self.caches)
        self.caches.append(cache)
        row=dict(call_id=len(self.records)+1,purpose=purpose,evaluation_id=evaluation_id,
            node=node,parent=parent,probe=probe.name,input=x.tolist(),soft_step=soft_step,
            received_fields=['vector','cache','support'],support=copy.deepcopy(support),
            cache_initial=copy.deepcopy(cache),cache_identity_unique=unique,status='entered')
        self.records.append(row)
        try:
            output=probe.run(track(x.copy()),cache,copy.deepcopy(support))
            row['cache_after']=copy.deepcopy(cache)
            if output.support!=support:raise ContractError('Output slot/window/condition contract mismatch')
            y=vector(output.value)
            if y.shape!=x.shape:raise ContractError('Output vector length mismatch')
            row.update(status='returned',output=y.tolist())
            return y
        except Exception as exc:
            row.update(status='rejected',error=type(exc).__name__+': '+str(exc),cache_after=copy.deepcopy(cache))
            raise


def evaluate(x,probe_a,probe_b,h,eta,support,ledger,evaluation_id,*,purpose='core'):
    """Exactly four successful probe calls. No automatic repeat diagnostics."""
    x=vector(x);h=scalar(h,'h');eta=scalar(eta,'eta');validate_support(support,len(x))
    if probe_a.deterministic is not True or probe_b.deterministic is not True:
        raise ContractError('Deterministic probe declaration required')
    before=len(ledger.records)
    ra=ledger.call(probe_a,x,support,purpose=purpose,evaluation_id=evaluation_id,node='Ra_x',parent='input',soft_step=h)
    rb=ledger.call(probe_b,x,support,purpose=purpose,evaluation_id=evaluation_id,node='Rb_x',parent='input',soft_step=h)
    ua=track((1-h)*x+h*ra);ub=track((1-h)*x+h*rb)
    rab=ledger.call(probe_a,ub,support,purpose=purpose,evaluation_id=evaluation_id,node='Ra_Pb',parent='Pb',soft_step=h)
    rba=ledger.call(probe_b,ua,support,purpose=purpose,evaluation_id=evaluation_id,node='Rb_Pa',parent='Pa',soft_step=h)
    uab=track((1-h)*ub+h*rab);uba=track((1-h)*ua+h*rba)
    k=track((uab-uba)/(h*h));va=track(ra-x);vb=track(rb-x)
    n=len(x);ek=float(k@k);ea=float(va@va);eb=float(vb@vb);den=ea+eb
    return dict(x=x.tolist(),ra=ra.tolist(),rb=rb.tolist(),pa=ua.tolist(),pb=ub.tolist(),
        ra_pb=rab.tolist(),rb_pa=rba.tolist(),endpoint_ab=uab.tolist(),endpoint_ba=uba.tolist(),
        K=k.tolist(),v_a=va.tolist(),v_b=vb.tolist(),dimension=n,h=h,eta_mean=eta,
        energy_sum=dict(K=ek,a=ea,b=eb,input=float(x@x)),
        energy_mean=dict(K=ek/n,a=ea/n,b=eb/n,input=float(x@x)/n),
        q_mean_fixed_eta=(ek/n)/(den/n+eta),
        q_sum_fixed_eta=ek/(den+eta),
        q_sum_eta_equivalent_to_mean=ek/(den+n*eta),eta_sum_equivalent_to_mean=n*eta,
        successful_core_calls=len(ledger.records)-before,
        paths=dict(ab=[probe_b.name,probe_a.name],ba=[probe_a.name,probe_b.name]),
        shared_nodes=['Pa','Pb'],call_ids=list(range(before+1,len(ledger.records)+1)))


def repeat_diagnostic(probe,x,support,ledger,diagnostic_id):
    """Two separately recorded calls, never counted inside four-call evaluate."""
    x=vector(x);validate_support(support,len(x));start=len(ledger.records)
    first=ledger.call(probe,x,support,purpose='diagnostic_repeat',evaluation_id=diagnostic_id,node='repeat1',parent='input')
    second=ledger.call(probe,x,support,purpose='diagnostic_repeat',evaluation_id=diagnostic_id,node='repeat2',parent='input')
    return dict(exactly_equal=bool(np.array_equal(first,second)),max_difference=float(abs(first-second).max()),
        diagnostic_calls=len(ledger.records)-start,
        limitation='Agreement of two mock calls does not prove general determinism or numerical accuracy')
