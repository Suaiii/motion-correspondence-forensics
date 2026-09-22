"""Independent arithmetic reference for AL84; does not import bridge or AL79."""
import numpy as np

def reference(trace):
    calls = {row["role"]: np.asarray(row["output"], dtype=np.float64) for row in trace["calls"]}
    inputs = {row["role"]: np.asarray(row["input"], dtype=np.float64) for row in trace["calls"]}
    h = float(trace["h"])
    x = inputs["Ra_x"]
    ra, rb = calls["Ra_x"], calls["Rb_x"]
    pa = np.add(np.multiply(1.0 - h, x), np.multiply(h, ra))
    pb = np.add(np.multiply(1.0 - h, x), np.multiply(h, rb))
    rab, rba = calls["Ra_Pb"], calls["Rb_Pa"]
    va = np.subtract(ra, x)
    vb = np.subtract(rb, x)
    da = np.divide(np.add(np.subtract(np.subtract(rab, pb), ra), x), h)
    db = np.divide(np.add(np.subtract(np.subtract(rba, pa), rb), x), h)
    uab = np.add(np.multiply(1.0 - h, pb), np.multiply(h, rab))
    uba = np.add(np.multiply(1.0 - h, pa), np.multiply(h, rba))
    return {"d_a": da, "d_b": db, "v_a": va, "v_b": vb, "K": np.divide(np.subtract(uab, uba), h*h)}
