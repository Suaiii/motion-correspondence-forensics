"""AL32 fixed arithmetic only. No optimizer, filtering, probe or classifier."""
import numpy as np


def stable_filter(record, counters):
    a = np.array(record['filtered_fields']['d_a'], dtype=np.float64)
    b = np.array(record['filtered_fields']['d_b'], dtype=np.float64)
    k = np.array(record['filtered_fields']['K'], dtype=np.float64)
    assert a.shape == b.shape == k.shape == tuple(record['support_shape'])
    assert a.size == record['support_elements'] == 54
    assert all(np.isfinite(v).all() for v in [a,b,k]) and record['D'] > 0
    s = a + b
    counters['field_array_additions'] += 1
    s2, sk = s*s, s*k
    counters['field_elementwise_products'] += 2
    numerator_s, numerator_j = float(np.mean(s2)), float(np.mean(sk))
    counters['field_mean_reductions'] += 2
    rs, rj = numerator_s / record['D'], numerator_j / record['D']
    counters['field_scalar_normalizations'] += 2
    rk = record['q_direct']  # Literal archived candidate value, never A+B-2C.
    counters['literal_q_reuses'] += 1
    return dict(s_H=s.tolist(), numerators=dict(S=numerator_s,J=numerator_j),
                r=[rs,rk,rj], r_hex=[float(v).hex() for v in [rs,rk,rj]],
                signs=dict(d_a=np.sign(a).tolist(),d_b=np.sign(b).tolist(),
                           K=np.sign(k).tolist(),s_H=np.sign(s).tolist(),
                           r=np.sign([rs,rk,rj]).astype(int).tolist()),
                max_array_bytes=max(v.nbytes for v in [a,b,k,s,s2,sk]))


def four_term_score(weights, features, counters):
    """Same explicit four multiplies and four accumulator additions for both paths."""
    assert len(weights) == len(features) == 4
    score = 0.0
    products, partial_sums = [], []
    for weight, feature in zip(weights,features):
        product = float(weight)*float(feature)
        score += product
        products.append(product)
        partial_sums.append(score)
    counters['four_term_score_calls'] += 1
    counters['score_scalar_multiplications'] += 4
    counters['score_accumulator_additions'] += 4
    return dict(value=score,hex=score.hex(),products=products,partial_sums=partial_sums)


def fixed_objective(differences, parameters, metric, regularizer, counters):
    """One fixed point; metric=I for beta or BB^T for gamma. Returns full derivatives."""
    assert differences.shape[1] == len(parameters) == 12
    assert 1 <= len(differences) <= 12
    margins = differences @ parameters
    e = np.exp(-np.abs(margins))
    negative_logistic_factor = np.where(margins >= 0,e/(1+e),1/(1+e))
    curvature = e/(1+e)**2
    data = float(np.mean(np.maximum(-margins,0)+np.log1p(e)))
    metric_x = metric @ parameters
    penalty = float(regularizer*(parameters @ metric_x))
    gradient_data = -(differences.T @ negative_logistic_factor)/len(margins)
    gradient_penalty = 2*regularizer*metric_x
    hessian_data = (differences.T*curvature) @ differences/len(margins)
    hessian_penalty = 2*regularizer*metric
    counters['fixed_objective_evaluations'] += 1
    counters['objective_matrix_products'] += 5  # D*x,G*x,x^T G*x,D^T f,D^T diag(c)D.
    counters['objective_data_mean_reductions'] += 1
    return dict(parameters=parameters.tolist(),margins=margins.tolist(),
                objective=data+penalty,data_term=data,penalty=penalty,
                gradient= (gradient_data+gradient_penalty).tolist(),
                gradient_data=gradient_data.tolist(),gradient_penalty=gradient_penalty.tolist(),
                hessian=(hessian_data+hessian_penalty).tolist(),
                hessian_data=hessian_data.tolist(),hessian_penalty=hessian_penalty.tolist())
