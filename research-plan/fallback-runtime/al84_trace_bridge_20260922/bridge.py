"""AL84 precomputed four-call identity bridge; no model invocation."""
from __future__ import annotations
import hashlib, math
import numpy as np

MAX_BYTES = 2 * 1024 * 1024
ROLES = ("Ra_x", "Rb_x", "Ra_Pb", "Rb_Pa")
EXPECTED = {
    "Ra_x": ("input", "a", "input"),
    "Rb_x": ("input", "b", "input"),
    "Ra_Pb": ("Pb", "a", "soft_b"),
    "Rb_Pa": ("Pa", "b", "soft_a"),
}

class BridgeInputError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def _array(value, name, shape):
    a = np.asarray(value, dtype=np.float64)
    if a.ndim != 5 or tuple(a.shape) != tuple(shape):
        raise BridgeInputError(name + "_shape")
    if a.nbytes > MAX_BYTES:
        raise BridgeInputError("array_limit")
    if not np.isfinite(a).all():
        raise BridgeInputError(name + "_nonfinite")
    return np.ascontiguousarray(a)

def _sha(a):
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes(order="C")).hexdigest()

def _same(a, b):
    return bool(np.allclose(a, b, rtol=1e-12, atol=1e-12, equal_nan=False))

def _meta(trace):
    required = {"sample_id", "stage", "probe_ids", "h", "support", "calls"}
    if set(trace) != required:
        raise BridgeInputError("trace_schema")
    sample_id = trace["sample_id"]
    stage = trace["stage"]
    probes = trace["probe_ids"]
    support = trace["support"]
    if not isinstance(sample_id, str) or not sample_id:
        raise BridgeInputError("sample_id")
    if stage != "OR1":
        raise BridgeInputError("stage")
    if not isinstance(probes, dict) or set(probes) != {"a", "b"}:
        raise BridgeInputError("probe_ids")
    if any(not isinstance(probes[k], str) or not probes[k] for k in ("a", "b")) or probes["a"] == probes["b"]:
        raise BridgeInputError("probe_ids")
    h = trace["h"]
    if isinstance(h, bool) or not isinstance(h, (int, float)) or not math.isfinite(float(h)) or not 0.0 < float(h) <= 1.0:
        raise BridgeInputError("h")
    if not isinstance(support, dict) or set(support) != {"layout", "shape", "time_slots", "channels", "clock_policy"}:
        raise BridgeInputError("support_schema")
    shape = support["shape"]
    if support["layout"] != "BTHWC" or support["channels"] != 3 or support["clock_policy"] != "mock_declared_grid":
        raise BridgeInputError("support_contract")
    if not isinstance(shape, list) or len(shape) != 5 or shape[-1] != 3 or any(isinstance(v, bool) or not isinstance(v, int) or v < 1 for v in shape):
        raise BridgeInputError("shape_contract")
    slots = support["time_slots"]
    if slots != list(range(shape[1])):
        raise BridgeInputError("time_slots")
    if shape[0] != 1 or shape[1] != 2 or shape[2] < 3 or shape[3] < 3:
        raise BridgeInputError("shape_contract")
    return sample_id, stage, probes, float(h), support, tuple(shape)

def bridge(trace):
    sample_id, stage, probes, h, support, shape = _meta(trace)
    calls = trace["calls"]
    if not isinstance(calls, list) or len(calls) != 4:
        raise BridgeInputError("call_count")
    rows = {}
    for row in calls:
        required = {"role", "parent", "probe_id", "input_ref", "sample_id", "stage", "shape",
                    "time_slots", "input", "output", "input_sha256", "output_sha256"}
        if not isinstance(row, dict) or set(row) != required:
            raise BridgeInputError("call_schema")
        role = row["role"]
        if role in rows:
            raise BridgeInputError("duplicate_role")
        if role not in EXPECTED:
            raise BridgeInputError("unknown_role")
        parent, probe_key, input_ref = EXPECTED[role]
        if (row["parent"], row["probe_id"], row["input_ref"]) != (parent, probes[probe_key], input_ref):
            raise BridgeInputError("role_binding")
        if row["sample_id"] != sample_id or row["stage"] != stage or row["shape"] != list(shape) or row["time_slots"] != support["time_slots"]:
            raise BridgeInputError("call_identity")
        inp = _array(row["input"], role + "_input", shape)
        out = _array(row["output"], role + "_output", shape)
        if row["input_sha256"] != _sha(inp) or row["output_sha256"] != _sha(out):
            raise BridgeInputError("tensor_hash")
        rows[role] = (inp, out)
    if set(rows) != set(ROLES):
        raise BridgeInputError("missing_role")
    x, ra = rows["Ra_x"]
    x_b, rb = rows["Rb_x"]
    if not _same(x, x_b):
        raise BridgeInputError("base_input_identity")
    pa = (1.0 - h) * x + h * ra
    pb = (1.0 - h) * x + h * rb
    pb_in, rab = rows["Ra_Pb"]
    pa_in, rba = rows["Rb_Pa"]
    if not _same(pb_in, pb):
        raise BridgeInputError("soft_b_input_identity")
    if not _same(pa_in, pa):
        raise BridgeInputError("soft_a_input_identity")
    va = ra - x
    vb = rb - x
    da = (rab - pb - ra + x) / h
    db = (rba - pa - rb + x) / h
    endpoint_ab = (1.0 - h) * pb + h * rab
    endpoint_ba = (1.0 - h) * pa + h * rba
    k_direct = (endpoint_ab - endpoint_ba) / (h * h)
    k_from_d = da - db
    if not _same(k_direct, k_from_d):
        raise BridgeInputError("k_consistency")
    fields = {"d_a": da, "d_b": db, "v_a": va, "v_b": vb}
    return {
        "sample_id": sample_id, "stage": stage, "probe_ids": probes, "h": h,
        "support": support, "shape": list(shape), "fields": fields,
        "pa": pa, "pb": pb, "ra_pb": rab, "rb_pa": rba,
        "endpoint_ab": endpoint_ab, "endpoint_ba": endpoint_ba,
        "K": k_direct, "K_from_d": k_from_d,
        "call_roles": list(ROLES),
    }
