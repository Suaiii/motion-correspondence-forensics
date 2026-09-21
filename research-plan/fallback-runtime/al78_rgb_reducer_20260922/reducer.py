"""AL78 explicit BTHWC/BCTHW RGB q/r reducer."""
import hashlib
import numpy as np

FILTERS = ("identity", "laplacian", "sobel_x", "sobel_y")
KERNELS = {
    "laplacian": np.asarray(((0,1,0),(1,-4,1),(0,1,0)), dtype=np.float64) / 4.0,
    "sobel_x": np.asarray(((-1,0,1),(-2,0,2),(-1,0,1)), dtype=np.float64) / 8.0,
    "sobel_y": np.asarray(((-1,-2,-1),(0,0,0),(1,2,1)), dtype=np.float64) / 8.0,
}
ETA = 1e-12

class ReducerInputError(ValueError): pass

def _canonical(x, layout):
    if not isinstance(x, np.ndarray) or x.dtype != np.float64 or x.ndim != 5:
        raise ReducerInputError("fields must be five-dimensional float64 arrays")
    if layout == "BTHWC": y = x
    elif layout == "BCTHW": y = np.transpose(x, (0,2,3,4,1))
    else: raise ReducerInputError("layout must be BTHWC or BCTHW")
    if y.shape[0] < 1 or y.shape[1] < 1 or y.shape[2] < 3 or y.shape[3] < 3 or y.shape[4] != 3:
        raise ReducerInputError("require B>=1,T>=1,H/W>=3,C=3")
    if not np.isfinite(y).all(): raise ReducerInputError("NaN/Inf input")
    return y

def _filter(x, name):
    if name == "identity": return x[:,:,1:-1,1:-1,:].copy()
    k=KERNELS[name]; out=np.zeros((x.shape[0],x.shape[1],x.shape[2]-2,x.shape[3]-2,x.shape[4]),dtype=np.float64)
    for dy in range(3):
        for dx in range(3):
            if k[dy,dx] != 0: out += x[:,:,dy:dy+out.shape[2],dx:dx+out.shape[3],:]*k[dy,dx]
    return out

def reduce_fields(fields, layout="BTHWC", blocks=None, _batch=True):
    if set(fields) != {"d_a","d_b","v_a","v_b"}: raise ReducerInputError("exact fields required")
    xs={k:_canonical(v,layout) for k,v in fields.items()}; shape=xs["d_a"].shape
    if any(v.shape != shape for v in xs.values()): raise ReducerInputError("shape mismatch")
    if blocks is None: blocks=[(0,shape[1])]
    if not blocks or blocks[0][0] != 0 or blocks[-1][1] != shape[1] or any(a>=b for a,b in blocks): raise ReducerInputError("invalid blocks")
    if any(b != c for (_,b),(c,_) in zip(blocks,blocks[1:])): raise ReducerInputError("non-contiguous blocks")
    k=xs["d_a"]-xs["d_b"]; s=xs["d_a"]+xs["d_b"]
    n=shape[0]*shape[1]*(shape[2]-2)*(shape[3]-2)*shape[4]
    out={"layout":layout,"input_shape":list(shape),"blocks":[list(x) for x in blocks],"eta":ETA,"filters":[],"batch":[]}
    for name in FILTERS:
        fk,fs,fva,fvb=[_filter(x,name) for x in (k,s,xs["v_a"],xs["v_b"])]
        sums={"k2":float(np.sum(fk*fk,dtype=np.float64)),"s2":float(np.sum(fs*fs,dtype=np.float64)),"sk":float(np.sum(fs*fk,dtype=np.float64)),"va2":float(np.sum(fva*fva,dtype=np.float64)),"vb2":float(np.sum(fvb*fvb,dtype=np.float64))}
        den=sums["va2"]+sums["vb2"]+n*ETA; q=sums["k2"]/den
        out["filters"].append({"name":name,"sums":sums,"denominator":den,"q_direct":q,"r_s":sums["s2"]/den,"r_k":q,"r_j":sums["sk"]/den,"q_hex":float(q).hex()})
    if _batch:
        for bi in range(shape[0]):
            one=reduce_fields({k:v[bi:bi+1] for k,v in xs.items()},"BTHWC",[(0,shape[1])],_batch=False)
            out["batch"].append(one["filters"])
    return out

def compare(a,b,atol=1e-12,rtol=1e-11):
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        e=abs(float(a)-float(b)); return e <= atol+rtol*max(abs(float(a)),abs(float(b)),1e-30),e
    if isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        z=[compare(x,y,atol,rtol) for x,y in zip(a,b)]; return all(x[0] for x in z),max([x[1] for x in z] or [0.0])
    if isinstance(a,dict) and isinstance(b,dict) and set(a)==set(b):
        z=[compare(a[k],b[k],atol,rtol) for k in a]; return all(x[0] for x in z),max([x[1] for x in z] or [0.0])
    return a==b,0.0

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
