"""Freeze then run AL79 once. Refuses to overwrite any run or freeze receipt."""
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "2"

import argparse
from datetime import datetime
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np
from reducer import reduce_fields, ReducerInputError
from reference import reference

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONFIG = HERE / "config.json"
FREEZE = HERE / "freeze.json"
OUT = HERE / "run_v1"


def now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, obj):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def freeze():
    files = [HERE / n for n in ("config.json", "reducer.py", "reference.py", "run_batch.py")]
    files.append(ROOT / "research-plan/AL79_PER_SAMPLE_STREAMING_RGB_CPU_20260922.md")
    protected = [p for p in (ROOT / "research-plan/fallback-runtime/al78_rgb_reducer_20260922").rglob("*")
                 if p.suffix in (".py", ".json", ".md")]
    protected += [ROOT / "research-runtime/algorithm_candidates/or1_filtered_readout/readout.py",
                  ROOT / "research-runtime/algorithm_candidates/or1_stable_baseline_reference/kernels.py"]
    obj = {"task_id": "AL79", "frozen_at": now(),
           "source_inputs": {p.relative_to(ROOT).as_posix(): sha(p) for p in files},
           "protected": {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(protected)}}
    write_new(FREEZE, obj)
    print(json.dumps({"frozen": True, "freeze_sha256": sha(FREEZE), "file_count": len(files), "protected": len(protected)}))


def fixture(spec):
    shape = tuple(spec["shape"])
    # All base grid entries are binary fractions, exactly representable in float64.
    bi, t, y, x, c = np.ogrid[tuple(slice(0, n) for n in shape)]
    fields = {
        "d_a": ((3 * bi + 5 * t + 7 * y + 11 * x + 13 * c) % 23 - 11).astype(np.float64) / 8,
        "d_b": ((2 * bi + 3 * t + 5 * y + 7 * x + 17 * c) % 19 - 9).astype(np.float64) / 16,
        "v_a": ((bi + t + y + 2 * x + c) % 13 - 6).astype(np.float64) / 8,
        "v_b": ((2 * bi + 2 * t + 3 * y + x + 2 * c) % 17 - 8).astype(np.float64) / 16,
    }
    kind = spec["kind"]
    if kind == "time_constants":
        for ti in range(shape[1]):
            fields["d_a"][:, ti].fill(ti + 1)
            fields["d_b"][:, ti].fill(0)
            fields["v_a"][:, ti].fill(2 ** ti)
            fields["v_b"][:, ti].fill(1)
    elif kind == "zero":
        for a in fields.values():
            a.fill(0)
    elif kind == "cancellation":
        fields["d_a"].fill(1)
        fields["d_b"].fill(1 - 2 ** -26)
        fields["v_a"].fill(1)
        fields["v_b"].fill(1)
    elif kind == "opposite":
        fields["d_b"] = -fields["d_a"]
    elif kind != "grid":
        raise ValueError(kind)
    return fields


def values(result):
    """Only numerical per-sample outputs, not differing layout/block metadata."""
    vals = []
    for sample in result["samples"]:
        vals += sample["q4"] + sample["r12"]
        for f in sample["filters"]:
            vals += [f["elements"], f["Dmean"], *f["sums"].values(), *f["means"].values()]
    return vals


def run():
    if OUT.exists():
        raise FileExistsError("run_v1 already exists; preserve it")
    frozen = json.loads(FREEZE.read_bytes())
    for group in ("source_inputs", "protected"):
        for p, h in frozen[group].items():
            if sha(ROOT / p) != h:
                raise ValueError(f"Pre-run frozen file changed: {p}")
    cfg = json.loads(CONFIG.read_bytes())
    OUT.mkdir()
    started = now()
    wall, cpu = time.perf_counter(), time.process_time()
    ev = {
        "task_id": "AL79", "version": cfg["version"], "started_at": started,
        "command": sys.argv, "cwd": str(Path.cwd()), "executor_role": "planagent",
        "freeze_sha256": sha(FREEZE), "source_inputs": frozen["source_inputs"],
        "python": sys.version, "numpy": np.__version__,
        "thread_environment": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
        "threads_created_by_script": 0, "native_blas_calls": 0, "peak_rss": None,
        "resources_scope": "Array sizes recorded, process peak RSS not measured; no BLAS linear algebra used",
        "calls": {"reducer": 0, "fraction_reference": 0, "network": 0, "server": 0, "media": 0, "models": 0, "gpu": 0, "optimizer": 0},
        "checks": [], "failures": [], "cases": [], "max_input_array_bytes": 0,
        "scope": "software_only_synthetic_rgb_fields", "independent_scientific_review": False,
    }
    write_new(OUT / "started.json", {"started_at": started, "freeze_sha256": sha(FREEZE)})

    def check(name, condition, **details):
        row = {"name": name, "passed": bool(condition), **details}
        ev["checks"].append(row)
        if not condition:
            ev["failures"].append(row)

    def close(name, actual, expected):
        av, bv = np.asarray(actual, dtype=np.float64), np.asarray(expected, dtype=np.float64)
        if av.shape != bv.shape:
            check(name, False, actual_shape=list(av.shape), expected_shape=list(bv.shape))
            return
        err = np.abs(av - bv)
        allowed = cfg["atol"] + cfg["rtol"] * np.abs(bv)
        check(name, np.isfinite(av).all() and np.isfinite(bv).all() and np.all(err <= allowed),
              max_abs_error=float(np.max(err)) if err.size else 0.0,
              max_tolerance_fraction=float(np.max(err / allowed)) if err.size else 0.0)

    def call(fields, layout="BTHWC", blocks=None):
        ev["calls"]["reducer"] += 1
        return reduce_fields(fields, layout, blocks)

    try:
        for spec in cfg["cases"]:
            fields = fixture(spec)
            ev["max_input_array_bytes"] = max(ev["max_input_array_bytes"], *(v.nbytes for v in fields.values()))
            assert all(v.nbytes <= cfg["max_array_bytes"] for v in fields.values())
            full = call(fields)
            blocked = call(fields, blocks=spec["blocks"])
            transposed = {k: v.transpose(0, 4, 1, 2, 3) for k, v in fields.items()}
            alternate = call(transposed, "BCTHW", spec["blocks"])
            row = {"id": spec["id"], "spec": spec,
                   "input_arrays": {k: {"shape": list(v.shape), "dtype": v.dtype.str, "bytes": v.nbytes,
                                         "sha256_c_order": hashlib.sha256(v.tobytes(order="C")).hexdigest()} for k, v in fields.items()},
                   "full": full, "blocked": blocked}
            ev["cases"].append(row)
            tag = spec["id"]
            close(tag + "/block_matches_full", values(blocked), values(full))
            close(tag + "/explicit_layout", values(alternate), values(blocked))
            for bi, sample in enumerate(blocked["samples"]):
                single = call({k: v[bi:bi + 1] for k, v in fields.items()}, blocks=spec["blocks"])
                close(f"{tag}/isolated_sample_{bi}", sample["q4"] + sample["r12"], values_head(single)[0])
            check(tag + "/shared_q_binary", all(
                float(q).hex() == float(s["r12"][3 * j + 1]).hex()
                for s in blocked["samples"] for j, q in enumerate(s["q4"])))
            spans = [tuple(x) for x in spec["blocks"]]
            check(tag + "/actual_time_slices", all(
                tuple(x["span"]) in spans and x["shape"][0] == x["span"][1] - x["span"][0]
                for x in blocked["metrics"]["filtered_input_shapes"]))
            check(tag + "/filter_call_count", blocked["metrics"]["filter_calls"] == spec["shape"][0] * len(spans) * 4 * 5,
                  observed=blocked["metrics"]["filter_calls"])
            check(tag + "/work_array_cap", blocked["metrics"]["max_work_array_bytes"] <= cfg["max_array_bytes"],
                  observed=blocked["metrics"]["max_work_array_bytes"])
            if spec["reference"] == "Fraction":
                ev["calls"]["fraction_reference"] += 1
                refs = reference(fields)
                row["rational_reference"] = refs
                for bi, (sample, ref) in enumerate(zip(blocked["samples"], refs)):
                    for got, exact in zip(sample["filters"], ref["filters"]):
                        keys = ("K2", "S2", "SK", "Va2", "Vb2")
                        actual = [got["elements"], got["Dmean"], got["q"], *got["r"], *(got["sums"][k] for k in keys)]
                        target = [exact["elements"], float(Fraction(exact["Dmean"])), float(Fraction(exact["q"])),
                                  *(float(Fraction(x)) for x in exact["r"]), *(float(Fraction(exact["sums"][k])) for k in keys)]
                        close(f"{tag}/fraction_{bi}_{got['filter']}", actual, target)
            if tag == "C1":
                swapped = call({k: v[::-1] for k, v in fields.items()}, blocks=spec["blocks"])
                close(tag + "/sample_order", values_head(swapped), list(reversed([s["q4"] + s["r12"] for s in blocked["samples"]])))
                check(tag + "/sample_signal_differs", blocked["samples"][0]["q4"] != blocked["samples"][1]["q4"])
            if tag == "C2":
                block_q = []
                for part in blocked["samples"][0]["blocks"]:
                    stats = part["filters"][0]
                    n, sums = stats["elements"], stats["sums"]
                    block_q.append((sums["K2"] / n) / ((sums["Va2"] + sums["Vb2"]) / n + cfg["eta"]))
                gap = abs(sum(block_q) / len(block_q) - blocked["samples"][0]["q4"][0])
                row["mean_of_block_ratios_negative_control"] = {"block_ratios": block_q, "equal_mean": sum(block_q) / len(block_q), "correct": blocked["samples"][0]["q4"][0], "gap": gap}
                check(tag + "/mean_ratio_counterexample", gap > cfg["ratio_negative_control_min_gap"], observed_gap=gap)
            if tag == "C3":
                check(tag + "/analytic_zero", all(x == 0 for x in values_head(blocked)[0]))
                check(tag + "/eta_denominator", all(f["Dmean"] == cfg["eta"] for f in blocked["samples"][0]["filters"]))
            if tag == "C4":
                expected = float(Fraction(1, 2 ** 52) / (2 + Fraction.from_float(cfg["eta"])))
                q = blocked["samples"][0]["q4"]
                # Relative error for the tiny q, because absolute tolerance alone is insufficient.
                check(tag + "/tiny_q_retained", q[0] > 0 and abs(q[0] / expected - 1) < 1e-11,
                      observed_q=q[0], expected_q=expected, relative_error=abs(q[0] / expected - 1))
                check(tag + "/constant_highpass_zero", q[1:] == [0.0, 0.0, 0.0])
            if tag == "C5":
                check(tag + "/no_full_time_filtered_array", max(x["shape"][0] for x in blocked["metrics"]["filtered_input_shapes"]) == 7)
            if tag == "C6":
                check(tag + "/opposite_field_nulls", all(f["r"][0] == f["r"][2] == 0 for f in blocked["samples"][0]["filters"]))
                cross = [Fraction(f["sums"]["AB"]) for f in row["rational_reference"][0]["filters"]]
                check(tag + "/signed_cross_negative", all(x < 0 for x in cross), exact=[str(v) for v in cross])

        # Reject cases exercise actual coded errors. Unexpected exceptions are failures.
        base_spec = cfg["cases"][0]
        for name in cfg["reject_cases"]:
            fields = fixture(base_spec)
            layout, blocks, want = "BTHWC", None, None
            if name == "missing_field":
                del fields["v_b"]; want = "field_schema"
            elif name == "shape_mismatch":
                fields["v_b"] = fields["v_b"][:, :, :, :-1, :]; want = "shape_mismatch"
            elif name in ("wrong_channels", "empty_interior", "empty_time", "empty_batch"):
                if name == "wrong_channels": fields = {k: v[..., :2] for k, v in fields.items()}
                if name == "empty_interior": fields = {k: v[:, :, :2] for k, v in fields.items()}
                if name == "empty_time": fields = {k: v[:, :0] for k, v in fields.items()}
                if name == "empty_batch": fields = {k: v[:0] for k, v in fields.items()}
                want = "domain"
            elif name == "unknown_layout": layout = "infer"; want = "layout"
            elif name == "float32": fields["d_a"] = fields["d_a"].astype(np.float32); want = "dtype_or_rank"
            elif name in ("nan", "infinity"):
                fields["d_a"].flat[0] = np.nan if name == "nan" else np.inf; want = "nonfinite_input"
            elif name == "array_cap":
                shape = (1, 1, 300, 300, 3)
                # Huge logical view backed by 3 scalars; reject before any allocation/read.
                fields = {k: np.broadcast_to(np.zeros((1, 1, 1, 1, 3), dtype=np.float64), shape) for k in fields}; want = "array_limit"
            elif name == "overflow": fields["d_a"].fill(1e308); want = "nonfinite_intermediate"
            else:
                blocks = {"float_block": [(0.0, 3)], "bool_block": [(False, 3)],
                          "negative_block": [(-1, 3)], "reversed_block": [(0, -1), (-1, 3)],
                          "empty_block": [], "overlap_block": [(0, 2), (1, 3)],
                          "gap_block": [(0, 1), (2, 3)], "incomplete_block": [(0, 2)]}[name]
                want = "blocks"
            try:
                call(fields, layout, blocks)
                check("reject/" + name, False, expected=want, observed="accepted")
            except ReducerInputError as exc:
                check("reject/" + name, exc.code == want, expected=want, observed=exc.code)
            except Exception as exc:
                check("reject/" + name, False, expected=want, observed=repr(exc))
    except Exception as exc:
        ev["fatal_error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        write_new(OUT / "error.json", ev["fatal_error"])
    finally:
        changed = [p for p, h in (frozen["source_inputs"] | frozen["protected"]).items() if sha(ROOT / p) != h]
        check("frozen_and_historical_unchanged", not changed, changed=changed)
        ev["finished_at"] = now()
        ev["wall_seconds"] = time.perf_counter() - wall
        ev["process_cpu_seconds"] = time.process_time() - cpu
        ev["software_pass"] = not ev["failures"] and "fatal_error" not in ev
        write_new(OUT / "evidence.json", ev)
    print(json.dumps({"software_pass": ev["software_pass"], "checks": len(ev["checks"]),
                      "failures": [x["name"] for x in ev["failures"]], "fatal_error": ev.get("fatal_error"),
                      "evidence_sha256": sha(OUT / "evidence.json"), "wall_seconds": ev["wall_seconds"]}, ensure_ascii=False))
    return 0 if ev["software_pass"] else 1


def values_head(result):
    return [s["q4"] + s["r12"] for s in result["samples"]]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "run"))
    args = parser.parse_args()
    if args.mode == "freeze": freeze()
    else: raise SystemExit(run())
