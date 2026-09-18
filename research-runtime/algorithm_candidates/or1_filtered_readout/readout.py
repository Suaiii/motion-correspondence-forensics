"""OR1-readout-1: fixed float64 THWC synthetic-field reference.
Correlation kernels, common valid interior, no clamping or learned readout.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='2'
import math
import numpy as np

FILTERS=('identity','laplacian','sobel_x','sobel_y')
NUMERATORS={
    'laplacian':((0,1,0),(1,-4,1),(0,1,0)),
    'sobel_x':((-1,0,1),(-2,0,2),(-1,0,1)),
    'sobel_y':((-1,-2,-1),(0,0,0),(1,2,1))}
DENOMINATORS={'laplacian':4,'sobel_x':8,'sobel_y':8}
ETA=np.float64(1e-12)

class ReadoutInputError(ValueError):
    def __init__(self,code,detail):
        super().__init__(detail);self.code=code


def track(array,metrics):
    metrics['max_array_bytes']=max(metrics.get('max_array_bytes',0),array.nbytes)
    if array.nbytes>1048576:raise ReadoutInputError('array_limit','Array exceeds 1 MiB')
    return array


def apply_filter(x,name,metrics):
    metrics['filter_applications']=metrics.get('filter_applications',0)+1
    if name=='identity':return track(x[:,1:-1,1:-1,:].copy(),metrics)
    kernel=track(np.asarray(NUMERATORS[name],dtype=np.float64)/DENOMINATORS[name],metrics)
    t,h,w,c=x.shape;vh,vw=h-2,w-2
    output=track(np.zeros((t,vh,vw,c),dtype=np.float64),metrics)
    for dy in range(3):
        for dx in range(3):
            if kernel[dy,dx]!=0:
                # Correlation: use the kernel in its written orientation.
                term=track(x[:,dy:dy+vh,dx:dx+vw,:]*kernel[dy,dx],metrics)
                output+=term
    return output


def compute(fields,metrics=None):
    if metrics is None:metrics={}
    metrics.setdefault('filter_applications',0);metrics.setdefault('max_array_bytes',0)
    if set(fields)!={'d_a','d_b','v_a','v_b'}:
        raise ReadoutInputError('field_schema','Exactly d_a/d_b/v_a/v_b required')
    for name,x in fields.items():
        if not isinstance(x,np.ndarray) or x.dtype!=np.float64 or x.ndim!=4:
            raise ReadoutInputError('input_type','Inputs must be float64 THWC arrays')
        track(x,metrics)
    shape=fields['d_a'].shape
    if any(x.shape!=shape for x in fields.values()):
        raise ReadoutInputError('shape_mismatch','All response fields must share one shape')
    t,h,w,c=shape
    if h<3 or w<3:raise ReadoutInputError('empty_valid_support','Spatial edge too short for common valid support')
    if not 1<=t<=2 or not 3<=h<=5 or not 3<=w<=5 or c!=3:
        raise ReadoutInputError('reference_domain','Require T1..2,H/W3..5,C3')
    if any(not np.isfinite(x).all() for x in fields.values()):
        raise ReadoutInputError('nonfinite_input','NaN/Inf response input rejected')
    records=[]
    try:
        with np.errstate(over='raise',invalid='raise',divide='raise'):
            k=track(fields['d_a']-fields['d_b'],metrics)
            arrays=fields|{'K':k}
            for name in FILTERS:
                f={key:apply_filter(value,name,metrics) for key,value in arrays.items()}
                def mean_product(a,b):
                    metrics['mean_products']=metrics.get('mean_products',0)+1
                    return float(np.mean(track(a*b,metrics),dtype=np.float64))
                n=mean_product(f['K'],f['K'])
                ea=mean_product(f['v_a'],f['v_a']);eb=mean_product(f['v_b'],f['v_b'])
                a=mean_product(f['d_a'],f['d_a']);b=mean_product(f['d_b'],f['d_b'])
                cross=mean_product(f['d_a'],f['d_b'])
                denominator=ea+eb+float(ETA)
                z=[a/denominator,b/denominator,cross/denominator]
                qdirect=n/denominator
                # Raw value deliberately retained; no abs(C), max(0,q), or eta change.
                qcompact=z[0]+z[1]-2*z[2]
                raw_n=a+b-2*cross
                values=[n,ea,eb,denominator,a,b,cross,qdirect,qcompact,raw_n]+z
                if not all(math.isfinite(value) for value in values):
                    raise ReadoutInputError('nonfinite_intermediate','Nonfinite filter/energy/ratio result')
                records.append(dict(filter=name,filtered_fields={key:value.tolist() for key,value in f.items()},
                    support_shape=list(f['K'].shape),support_elements=f['K'].size,
                    N=n,E_a=ea,E_b=eb,D=denominator,A=a,B=b,C=cross,z=z,
                    q_direct=qdirect,q_compact_raw=qcompact,q_compact_minus_direct=qcompact-qdirect,
                    compact_numerator_raw=raw_n,q_compact_numerator_first_diagnostic=raw_n/denominator,
                    compact_negative=qcompact<0,
                    denominator_mode='observed_eta_only' if ea+eb==0 else 'observed_residual_plus_eta',
                    AE_error_bound_status='unknown',source_decision=None))
    except FloatingPointError as exc:
        raise ReadoutInputError('nonfinite_intermediate',str(exc)) from exc
    return dict(version='OR1-readout-1',layout='THWC',dtype='float64',input_shape=list(shape),
        raw_elements_per_field=math.prod(shape),common_support_shape=[t,h-2,w-2,c],
        common_support_elements=t*(h-2)*(w-2)*c,
        spatial_indices=[(r,col) for r in range(1,h-1) for col in range(1,w-1)],
        eta_float=float(ETA),eta_float_hex=float(ETA).hex(),K=k.tolist(),filters=records,
        q4_direct=[r['q_direct'] for r in records],q4_compact_raw=[r['q_compact_raw'] for r in records],
        z12=[value for r in records for value in r['z']],
        z12_role='Compact readout triplets, not the 12-dimensional matching descriptor b',
        numeric_convention='Mean across all T, valid H, valid W and C elements; no padding or resampling',
        metrics=dict(metrics),classifier_fitted=False,classification_probabilities_produced=False,
        real_AE_error_bounds='unknown')
