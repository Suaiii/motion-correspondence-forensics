"""AL27 original-coordinate synthetic pairwise convex reference; no classifier."""
import numpy as np


class Ledger:
    def __init__(self, differences, regularizer):
        self.d = differences
        self.regularizer = regularizer
        self.evaluations = []

    def evaluate(self, x, purpose):
        m = self.d @ x
        e = np.exp(-np.abs(m))
        negative_sigmoid = np.where(m >= 0, e / (1 + e), 1 / (1 + e))
        curvature = e / (1 + e) ** 2
        data = float(np.mean(np.maximum(-m, 0) + np.log1p(e)))
        reg = float(self.regularizer * (x @ x))
        gradient = -(self.d.T @ negative_sigmoid) / len(m) + 2 * self.regularizer * x
        hessian = (self.d.T * curvature) @ self.d / len(m) + 2 * self.regularizer * np.eye(len(x))
        record = dict(id=len(self.evaluations), purpose=purpose, parameters=x.tolist(),
                      objective=data + reg, data_term=data, regularizer_term=reg,
                      gradient=gradient.tolist(), hessian=hessian.tolist(),
                      gradient_l2=float(np.linalg.norm(gradient)))
        self.evaluations.append(record)
        return record, gradient, hessian


def solve(differences, regularizer, config):
    if differences.ndim != 2 or not np.isfinite(differences).all():
        raise ValueError('nonfinite_or_invalid_input')
    ledger = Ledger(differences, regularizer)
    if len(differences) == 0:
        return dict(status='no_training_support', parameters=None, iterations=0,
                    steps=[], evaluations=[], terminal_evaluation_id=None), ledger
    x = np.zeros(differences.shape[1], dtype=np.float64)
    current, g, h = ledger.evaluate(x, 'initial_zero')
    steps = []
    status = 'maximum_iterations'
    for iteration in range(config['max_iterations'] + 1):
        if current['gradient_l2'] <= config['gradient_l2_tolerance']:
            status = 'gradient_l2_tolerance'
            break
        if iteration == config['max_iterations']:
            break
        step = dict(iteration=iteration, from_evaluation_id=current['id'], trials=[])
        steps.append(step)
        try:
            direction = np.linalg.solve(h, -g)
        except np.linalg.LinAlgError as exc:
            step['linear_solve'] = dict(status='failed', error=str(exc))
            status = 'linear_solve_failure'
            break
        directional = float(g @ direction)
        step['linear_solve'] = dict(status='solved', rhs=(-g).tolist(), direction=direction.tolist(),
                                   residual_l2=float(np.linalg.norm(h @ direction + g)),
                                   gradient_dot_direction=directional)
        if not np.isfinite(direction).all() or not directional < 0:
            status = 'invalid_descent_direction'
            break
        accepted = False
        for halving in range(config['maximum_halvings'] + 1):
            alpha = 2.0 ** -halving
            trial_x = x + alpha * direction
            trial, trial_g, trial_h = ledger.evaluate(trial_x, 'armijo_trial')
            bound = current['objective'] + config['armijo_c'] * alpha * directional
            accepted = bool(trial['objective'] <= bound)
            step['trials'].append(dict(alpha=alpha, evaluation_id=trial['id'],
                                       armijo_bound=bound, accepted=accepted))
            if accepted:
                x, current, g, h = trial_x, trial, trial_g, trial_h
                step['accepted_alpha'] = alpha
                break
        if not accepted:
            status = 'minimum_step_reached_without_acceptance'
            break
    return dict(status=status, parameters=x.tolist(),
                iterations=sum('accepted_alpha' in item for item in steps), steps=steps,
                evaluations=ledger.evaluations, terminal_evaluation_id=current['id']), ledger
