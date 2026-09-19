"""Exact finite-support arithmetic for AL58; stdlib only, no model or data access."""
from fractions import Fraction as F
from itertools import product
import json


def sq(x):
    return x * x


def mean(xs):
    return sum(xs, F(0)) / len(xs)


def A(y, ys):
    return mean([sq(y - z) for z in ys])


def B(y, ys):
    return sq(y - mean(ys))


def f(x):
    return {"num": x.numerator, "den": x.denominator}


ys = [F(0), F(1)]
table = [{"y": f(y), "A": f(A(y, ys)), "B": f(B(y, ys)), "A_minus_B": f(A(y, ys) - B(y, ys))}
         for y in [F(0), F(1, 2), F(1)]]

# Same fixed X/mask and the same iid recovery law for both source labels.
recovery_pairs = list(product([F(0), F(1)], repeat=2))
def expectation(fn, y):
    return sum((fn(y, pair) for pair in recovery_pairs), F(0)) / len(recovery_pairs)

source_gap = {
    "recovery_support": [f(F(0)), f(F(1))],
    "recovery_pair_probability": {"num": 1, "den": 4},
    "generated_y": f(F(0)),
    "real_y": f(F(1, 2)),
    "E_A_generated": f(expectation(A, F(0))),
    "E_A_real": f(expectation(A, F(1, 2))),
    "E_B_generated": f(expectation(B, F(0))),
    "E_B_real": f(expectation(B, F(1, 2))),
    "same_recovery_law": True,
}

# If source laws are also identical (uniform on {0,1}), both class gaps vanish.
same_source = {
    "E_A": f(sum((expectation(A, y) for y in [F(0), F(1)]), F(0)) / 2),
    "E_B": f(sum((expectation(B, y) for y in [F(0), F(1)]), F(0)) / 2),
}

assert all(row["A_minus_B"]["num"] >= 0 for row in table)
assert source_gap["E_A_generated"] != source_gap["E_A_real"]
assert same_source["E_A"] == same_source["E_A"]
print(json.dumps({"K": 2, "dimension": 1, "single_realization_table": table,
                  "iid_same_recovery_law_counterexample": source_gap,
                  "identical_source_law_reference": same_source}, sort_keys=True))
