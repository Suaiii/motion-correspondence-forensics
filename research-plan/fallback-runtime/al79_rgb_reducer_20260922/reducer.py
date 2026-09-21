"""Frozen RGB readout only. No reconstructor, training or input/output code.

Fields contain already-scaled d_a/d_b: K=d_a-d_b. Readout chunking does not
change any reconstructor's temporal context. Every returned item is one sample.
"""
import math
import numpy as np

FIELDS = ("d_a", "d_b", "v_a", "v_b")
FILTERS = ("identity", "laplacian", "sobel_x", "sobel_y")
KERNELS = {
    "laplacian": (((0, 1, 0), (1, -4, 1), (0, 1, 0)), 4),
    "sobel_x": (((-1, 0, 1), (-2, 0, 2), (-1, 0, 1)), 8),
    "sobel_y": (((-1, -2, -1), (0, 0, 0), (1, 2, 1)), 8),
}
ETA = 1e-12
MAX_ARRAY_BYTES = 2 * 1024 * 1024


class ReducerInputError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _input(fields, layout):
    if not isinstance(fields, dict) or set(fields) != set(FIELDS):
        raise ReducerInputError("field_schema")
    if layout not in ("BTHWC", "BCTHW"):
        raise ReducerInputError("layout")
    canonical = {}
    for key in FIELDS:
        value = fields[key]
        if not isinstance(value, np.ndarray) or value.ndim != 5 or value.dtype != np.float64:
            raise ReducerInputError("dtype_or_rank")
        if value.nbytes > MAX_ARRAY_BYTES:
            raise ReducerInputError("array_limit")
        if not np.isfinite(value).all():
            raise ReducerInputError("nonfinite_input")
        canonical[key] = value if layout == "BTHWC" else value.transpose(0, 2, 3, 4, 1)
    shape = canonical["d_a"].shape
    if any(x.shape != shape for x in canonical.values()):
        raise ReducerInputError("shape_mismatch")
    b, t, h, w, c = shape
    if b < 1 or t < 1 or h < 3 or w < 3 or c != 3:
        raise ReducerInputError("domain")
    return canonical, shape


def _blocks(blocks, length):
    if blocks is None:
        return [(0, length)]
    if not isinstance(blocks, (list, tuple)) or not blocks:
        raise ReducerInputError("blocks")
    result = []
    expected = 0
    for block in blocks:
        if not isinstance(block, (list, tuple)) or len(block) != 2:
            raise ReducerInputError("blocks")
        if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) for v in block):
            raise ReducerInputError("blocks")
        start, end = map(int, block)
        if start != expected or end <= start or end > length:
            raise ReducerInputError("blocks")
        result.append((start, end))
        expected = end
    if expected != length:
        raise ReducerInputError("blocks")
    return result


def _track(array, metrics):
    metrics["max_work_array_bytes"] = max(metrics["max_work_array_bytes"], array.nbytes)
    if array.nbytes > MAX_ARRAY_BYTES:
        raise ReducerInputError("array_limit")
    if not np.isfinite(array).all():
        raise ReducerInputError("nonfinite_intermediate")
    return array


def _filter(x, name, metrics):
    # x: one sample, one temporal block, THWC. Spatial correlation only.
    if name == "identity":
        return _track(x[:, 1:-1, 1:-1, :].copy(), metrics)
    kernel, divisor = KERNELS[name]
    out = _track(np.zeros((x.shape[0], x.shape[1] - 2, x.shape[2] - 2, 3), dtype=np.float64), metrics)
    for dy in range(3):
        for dx in range(3):
            weight = kernel[dy][dx] / divisor
            if weight:
                term = _track(x[:, dy:dy + out.shape[1], dx:dx + out.shape[2], :] * weight, metrics)
                out += term
    return _track(out, metrics)


def _product_sum(left, right, metrics):
    value = float(np.sum(_track(left * right, metrics), dtype=np.float64))
    if not math.isfinite(value):
        raise ReducerInputError("nonfinite_intermediate")
    return value


def reduce_fields(fields, layout="BTHWC", blocks=None):
    canonical, shape = _input(fields, layout)
    spans = _blocks(blocks, shape[1])
    metrics = {"max_work_array_bytes": 0, "filter_calls": 0, "filtered_input_shapes": []}
    samples = []
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            for sample_index in range(shape[0]):
                fragments = []
                for start, end in spans:
                    chunk = {k: canonical[k][sample_index, start:end] for k in FIELDS}
                    delta = _track(chunk["d_a"] - chunk["d_b"], metrics)
                    metrics["filtered_input_shapes"].append({"sample": sample_index, "span": [start, end], "shape": list(delta.shape)})
                    filtered_stats = []
                    for name in FILTERS:
                        ha, hb, hk, hva, hvb = [_filter(a, name, metrics) for a in (chunk["d_a"], chunk["d_b"], delta, chunk["v_a"], chunk["v_b"])]
                        metrics["filter_calls"] += 5
                        total = _track(ha + hb, metrics)
                        sums = {
                            "K2": _product_sum(hk, hk, metrics),
                            "S2": _product_sum(total, total, metrics),
                            "SK": _product_sum(total, hk, metrics),
                            "Va2": _product_sum(hva, hva, metrics),
                            "Vb2": _product_sum(hvb, hvb, metrics),
                        }
                        filtered_stats.append({"filter": name, "elements": int(hk.size), "sums": sums})
                    fragments.append({"start": start, "end": end, "filters": filtered_stats})
                q4, r12, finals = [], [], []
                for fi, name in enumerate(FILTERS):
                    parts = [f["filters"][fi] for f in fragments]
                    count = sum(f["elements"] for f in parts)
                    sums = {k: math.fsum(f["sums"][k] for f in parts) for k in ("K2", "S2", "SK", "Va2", "Vb2")}
                    means = {k: v / count for k, v in sums.items()}
                    denominator = means["Va2"] + means["Vb2"] + ETA
                    q = means["K2"] / denominator
                    r_s, r_j = means["S2"] / denominator, means["SK"] / denominator
                    if not all(math.isfinite(v) for v in [*sums.values(), denominator, q, r_s, r_j]):
                        raise ReducerInputError("nonfinite_intermediate")
                    q4.append(q)
                    r12.extend((r_s, q, r_j))
                    finals.append({"filter": name, "elements": count, "sums": sums, "means": means,
                                   "Dmean": denominator, "q": q, "r": [r_s, q, r_j]})
                samples.append({"sample_index": sample_index, "q4": q4, "r12": r12, "filters": finals, "blocks": fragments})
    except (FloatingPointError, OverflowError) as exc:
        raise ReducerInputError("nonfinite_intermediate") from exc
    return {"version": "rgb-reducer-v2", "canonical_shape": list(shape), "layout_received": layout,
            "samples": samples, "metrics": metrics, "eta": ETA}
