"""AL39 exact feature containment audit; reads only frozen AL32 evidence."""
from datetime import datetime, timezone
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

MAIN = Path("E:/aNB/TECH/脉冲神经网络")
WORK = Path("D:/SUAI/codex/worktree/662f/脉冲神经网络")
RUN = WORK / "research-runs/algorithm_search_20260918"
OUT = MAIN / "research-plan/reviews/AL39_FEATURE_CONTAINMENT_EXACT_20260919.json"

def mm(a, b):
    return [[sum(x*y for x, y in zip(row, col)) for col in zip(*b)] for row in a]

def mv(a, x):
    return [sum(v*w for v, w in zip(row, x)) for row in a]

def transpose(a):
    return [list(row) for row in zip(*a)]

def strings(value):
    if isinstance(value, list):
        return [strings(v) for v in value]
    return str(value)

def main():
    inputs = json.loads((RUN/"AL32_inputs.json").read_text(encoding="utf-8"))
    evidence = json.loads((RUN/"AL32_evidence.json").read_text(encoding="utf-8"))
    config = json.loads((RUN/"AL32_config.json").read_text(encoding="utf-8"))
    assert evidence["gate_result"] == "pass" and len(evidence["checks"]) == 85
    assert json.loads((RUN/"AL27_evidence.json").read_text(encoding="utf-8"))["gate_result"] == "fail"
    block = [[F(v) for v in row] for row in config["B"]]
    P = [[F(i == 3*k+1) for i in range(12)] for k in range(4)]
    weights = [F(v) for v in config["weights"]]
    fixed_weights = [weights, [F(1), F(1), F(-1), F(1, 2)]]
    fixed_weight_checks = []
    for w in fixed_weights:
        gamma = mv(transpose(P), w)
        beta = mv(transpose(block), gamma)
        fixed_weight_checks.append({"w": strings(w), "gamma": strings(gamma), "beta": strings(beta)})
    field_checks = []
    for selected, archived in zip(inputs["archived_fields"], evidence["archived_field_processing"]):
        stable = archived["r12"]
        q = [F.from_float(v) for v in selected["q4_direct"]]
        r = [F.from_float(v) for v in stable]
        chosen = mv(P, r)
        assert chosen == q
        for w in fixed_weights:
            assert sum(a*b for a,b in zip(w, chosen)) == sum(a*b for a,b in zip(mv(transpose(P),w), r))
        field_checks.append({"id": selected["id"], "q_equals_Pr": True, "q_hex": [v.hex() for v in selected["q4_direct"]]})
    G = mm(block, transpose(block))
    lambda_free = F(1, 6000)
    regularizer_checks = []
    for w in fixed_weights:
        gamma = mv(transpose(P), w)
        beta = mv(transpose(block), gamma)
        left = lambda_free * sum(v*v for v in beta)
        right = lambda_free * sum(a*b for a,b in zip(gamma, mv(G, gamma)))
        candidate = F(1, 1000) * sum(v*v for v in w)
        assert left == right == candidate
        regularizer_checks.append({"w": strings(w), "beta_penalty": str(left), "gamma_penalty": str(right), "candidate_penalty": str(candidate)})
    result = {
        "task_id": "AL39", "created_at": datetime.now(timezone.utc).isoformat(),
        "gate_result": "pass", "gate_scope": "feature_containment_capacity_math",
        "checks": [
            {"name": "fixed_selection_matrix_shape", "passed": True},
            {"name": "q_equals_P_r_on_12_archived_records", "passed": True},
            {"name": "score_identity_for_two_fixed_weights", "passed": True},
            {"name": "induced_regularizer_matches_candidate_on_fixed_subspace", "passed": True},
            {"name": "no_fitting_or_label_access", "passed": True}
        ],
        "selection_matrix": strings(P), "fixed_weight_checks": fixed_weight_checks,
        "field_checks": field_checks, "regularizer_checks": regularizer_checks,
        "interpretation": {
            "supported": "The four-dimensional q is a fixed coordinate selection from the frozen twelve-dimensional r on archived reference fields; the candidate score is contained by the stable linear readout class under the declared induced regularizer on the fixed subspace.",
            "not_supported": ["real model efficacy", "capacity-matched generalization", "new algorithm admission", "source classification gain"],
            "fairness_boundary": "A common lambda string is not an identical regularizer in gamma coordinates; training, calibration and model capacity remain untested."
        },
        "resources": {"stdlib_fraction_only": True, "real_samples_accessed": False, "model_calls": 0, "training_calls": 0, "server_calls": 0, "gpu_calls": 0, "optimizer_calls": 0},
        "upstream_hashes": {rel: hashlib.sha256((RUN/rel).read_bytes()).hexdigest() for rel in ["AL32_inputs.json", "AL32_evidence.json", "AL32_config.json"]}
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"gate_result": "pass", "fields": len(field_checks), "weights": len(fixed_weights)}))

if __name__ == "__main__":
    main()
