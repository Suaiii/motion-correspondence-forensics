"""AL34 exact single-step Gram sufficiency audit; stdlib only, fixed inputs."""
from datetime import datetime, timezone
from fractions import Fraction as F
import json
from pathlib import Path

OUT = Path(__file__).with_name("AL34_SINGLE_STEP_EXACT_20260919.json")


def eye(n):
    return [[F(i == j) for j in range(n)] for i in range(n)]


def mm(a, b):
    return [[sum(x*y for x, y in zip(row, col)) for col in zip(*b)] for row in a]


def mv(a, x):
    return [sum(v*w for v, w in zip(row, x)) for row in a]


def sub(a, b):
    return [[x-y for x, y in zip(row, row_b)] for row, row_b in zip(a, b)]


def add(a, b):
    return [[x+y for x, y in zip(row, row_b)] for row, row_b in zip(a, b)]


def scale(a, s):
    return [[s*x for x in row] for row in a]


def transpose(a):
    return [list(row) for row in zip(*a)]


def block_diag(*blocks):
    n = sum(len(block) for block in blocks)
    out = [[F(0) for _ in range(n)] for _ in range(n)]
    offset = 0
    for block in blocks:
        for i, row in enumerate(block):
            for j, value in enumerate(row):
                out[offset+i][offset+j] = value
        offset += len(block)
    return out


def gram(vectors):
    return [[sum(a*b for a, b in zip(x, y)) for y in vectors] for x in vectors]


def norm2(x):
    return sum(v*v for v in x)


def strings(value):
    if isinstance(value, list):
        return [strings(v) for v in value]
    return str(value)


def main():
    zero = F(0)
    one = F(1)
    J = [[one, zero], [zero, zero]]
    L = [[zero, zero], [zero, one]]
    Q = [[F(9, 25), F(12, 25)], [F(12, 25), F(16, 25)]]
    A = block_diag(J, J, J, [[zero]])
    B = block_diag(J, Q, L, [[zero]])
    x = [zero, zero, F(5), zero, zero, zero, one]
    y = [F(3), zero, zero, zero, F(4), zero, one]
    assert len(A) == len(B) == len(x) == len(y) == 7
    checks = []

    def check(name, passed, **details):
        checks.append(dict(name=name, passed=bool(passed), **details))
        assert passed, (name, details)

    for name, matrix in [('A', A), ('B', B)]:
        check(name+'/symmetric', matrix == transpose(matrix))
        check(name+'/idempotent', mm(matrix, matrix) == matrix)
    comm = sub(mm(A, B), mm(B, A))
    # h-polynomial coefficients: constant/linear commute; quadratic is [A,B].
    # No h sweep is needed to verify the all-h identity.
    identity = eye(7)
    check('finite_h_constant_commutes', sub(mm(identity, identity), mm(identity, identity)) == scale(identity, zero))
    da = sub(A, identity)
    db = sub(B, identity)
    check('finite_h_quadratic_coefficient', sub(mm(da, db), mm(db, da)) == comm)

    c = sub(A, B)
    c2 = mm(c, c)
    c4 = mm(c2, c2)
    comm_t_comm = mm(transpose(comm), comm)
    check('projection_identity_C2_minus_C4', comm_t_comm == sub(c2, c4))
    kx = mv(comm, x)
    ky = mv(comm, y)
    check('x_commutator_nonzero', norm2(kx) == F(144, 25), value=str(norm2(kx)))
    check('y_commutator_zero', norm2(ky) == zero, value=str(norm2(ky)))

    gram_x = gram([x, mv(A, x), mv(B, x)])
    gram_y = gram([y, mv(A, y), mv(B, y)])
    check('complete_single_step_gram_equal', gram_x == gram_y, gram=strings(gram_x))
    check('input_norm_equal', norm2(x) == norm2(y), value=str(norm2(x)))
    ax, bx = mv(A, x), mv(B, x)
    ay, by = mv(A, y), mv(B, y)
    residual_x = norm2([a-b for a,b in zip(ax,x)]) + norm2([a-b for a,b in zip(bx,x)])
    residual_y = norm2([a-b for a,b in zip(ay,y)]) + norm2([a-b for a,b in zip(by,y)])
    check('ordinary_two_call_residual_equal', residual_x == residual_y, value=str(residual_x))
    check('ordinary_cross_terms_equal', [sum(a*b for a, b in zip(u, v)) for u, v in [(x, ax), (x, bx), (ax, bx)]] ==
          [sum(a*b for a, b in zip(u, v)) for u, v in [(y, ay), (y, by), (ay, by)]])

    eta = F(1, 10**12)
    qx = F(1, 7)*norm2(kx) / (F(1, 7)*residual_x + eta)
    qy = F(1, 7)*norm2(ky) / (F(1, 7)*residual_y + eta)
    check('normalized_response_separates_fixed_vectors', qx != qy, qx=str(qx), qy=str(qy))
    check('same_denominator_different_numerator', residual_x == residual_y and norm2(kx) != norm2(ky))
    result = {
        'task_id': 'AL34',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'gate_result': 'pass',
        'gate_scope': 'single_step_Gram_sufficiency_math',
        'checks': checks,
        'matrices': {'A': strings(A), 'B': strings(B), 'Q': strings(Q), 'commutator': strings(comm)},
        'vectors': {'x': strings(x), 'y': strings(y), 'Ax': strings(ax), 'Bx': strings(bx), 'Ay': strings(ay), 'By': strings(by)},
        'finite_h': 'Symbolic polynomial cancellation: (I+h(A-I))(I+h(B-I)) minus reversed order equals h^2(AB-BA).',
        'gram_x': strings(gram_x), 'gram_y': strings(gram_y),
        'residual_sum_x': str(residual_x), 'residual_sum_y': str(residual_y),
        'commutator_energy_x': str(norm2(kx)), 'commutator_energy_y': str(norm2(ky)),
        'q_eta_1e-12_x': str(qx), 'q_eta_1e-12_y': str(qy),
        'interpretation': {
            'supported': 'The complete single-step Gram of (x,Ax,Bx), input norm, and ordinary two-call residuals do not determine commutator energy under this fixed projection construction.',
            'not_supported': ['real AE mechanism', 'four-filter OR1 refutation', 'source classification gain', 'cross-domain generalization', 'new algorithm admission'],
            'failure_boundary': 'This is one exact finite-dimensional counterexample; it does not show that a richer feature set or actual decoder has the same behavior.'
        },
        'resource': {'stdlib_only': True, 'model_calls': 0, 'media_calls': 0, 'server_calls': 0, 'gpu_calls': 0, 'classifier_training_calls': 0, 'selected_constructions': 1}
    }
    with OUT.open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'gate_result': 'pass', 'checks': len(checks), 'qx': str(qx), 'qy': str(qy)}))


if __name__ == '__main__':
    main()
