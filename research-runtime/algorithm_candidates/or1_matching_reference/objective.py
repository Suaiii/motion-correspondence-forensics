"""Prespecified scalar subproblem of a four-dimensional convex objective.
No real detector fitting, no probabilities, and no floating-point certificate.
"""
import math

class ObjectiveInputError(ValueError):pass


def validate_differences(differences):
    if len(differences)>4:raise ObjectiveInputError('At most four mathematical pairs')
    out=[]
    for row in differences:
        if len(row)!=4:raise ObjectiveInputError('q/difference dimension is four')
        values=tuple(float(x) for x in row)
        if not all(math.isfinite(x) for x in values):raise ObjectiveInputError('Nonfinite difference')
        if any(x!=0 for x in values[1:]):raise ObjectiveInputError('This reference solves only the predefined first-coordinate inputs')
        out.append(values)
    return tuple(out)


def softplus(x):return max(x,0.)+math.log1p(math.exp(-abs(x)))


class FixedObjective:
    def __init__(self,differences,lam=.001):
        if lam!=.001:raise ObjectiveInputError('Original lambda remains 1e-3')
        self.differences=validate_differences(differences);self.lam=lam;self.calls=0

    def evaluate(self,t):
        if not self.differences:raise ObjectiveInputError('Empty pair mean is undefined')
        t=float(t)
        if not math.isfinite(t):raise ObjectiveInputError('Finite scalar coordinate required')
        self.calls+=1;w=(t,0.,0.,0.);count=len(self.differences)
        margins=[t*d[0] for d in self.differences]
        if not all(math.isfinite(m) for m in margins):raise ObjectiveInputError('Margin overflow')
        negative_sigmoid=[];curvatures=[]
        for margin in margins:
            e=math.exp(-abs(margin));curvatures.append(e/(1+e)**2)
            negative_sigmoid.append(e/(1+e) if margin>=0 else 1/(1+e))
        value=math.fsum(softplus(-m) for m in margins)/count+self.lam*t*t
        gradient=[-math.fsum(d[j]*s for d,s in zip(self.differences,negative_sigmoid))/count+2*self.lam*w[j] for j in range(4)]
        hessian=[[math.fsum(c*d[j]*d[k] for d,c in zip(self.differences,curvatures))/count+(2*self.lam if j==k else 0.)
                  for k in range(4)] for j in range(4)]
        if not all(math.isfinite(x) for x in [value]+gradient+[x for r in hessian for x in r]):raise ObjectiveInputError('Nonfinite objective arithmetic')
        return dict(w=w,value=value,gradient=gradient,hessian=hessian,
            arithmetic='ordinary binary64 numeric check, not a rigorous error-certified value')


def solve_first_coordinate(objective,bracket=(-16.,16.),width_tolerance=1e-12,max_iterations=128):
    if not objective.differences:
        return dict(status='no_training_support',w=None,value=None,iterations=0,objective_evaluations=0,
            reason='Empty matching is not a nonempty zero-difference objective')
    before=objective.calls
    if all(d[0]==0 for d in objective.differences):
        value=objective.evaluate(0.)
        return dict(status='analytic_zero_difference_control',solution=value,iterations=0,objective_evaluations=objective.calls-before,
            reason='Nonempty objective is log(2)+lambda*t^2; t=0 analytically, displayed loss is numeric')
    left,right=bracket;el=objective.evaluate(left);er=objective.evaluate(right)
    if not el['gradient'][0]<0<er['gradient'][0]:
        return dict(status='fixed_bracket_failed',initial_left=el,initial_right=er,iterations=0,
            objective_evaluations=objective.calls-before,w=None)
    history=[];reason=None
    for iteration in range(1,max_iterations+1):
        mid=(left+right)/2;value=objective.evaluate(mid);g=value['gradient'][0]
        history.append(dict(iteration=iteration,t=mid,value=value['value'],gradient=g,hessian_00=value['hessian'][0][0]))
        if g==0:
            left=right=mid;reason='floating_gradient_zero';break
        if g<0:left=mid
        else:right=mid
        if right-left<=width_tolerance:
            reason='floating_bracket_width';break
    if reason is None:
        return dict(status='iteration_limit',iterations=max_iterations,history=history,objective_evaluations=objective.calls-before,w=None)
    solution=objective.evaluate((left+right)/2)
    return dict(status='numerical_scalar_solution',solution=solution,iterations=iteration,stop_reason=reason,
        floating_bracket=(left,right),bracket_width=right-left,absolute_computed_gradient=abs(solution['gradient'][0]),
        objective_evaluations=objective.calls-before,history=history,
        rigorous_parameter_error_bound=None,
        limitation='Gradient/exp rounding error has no certified bound; this is not an AL18-style exact certificate')
