"""Independent scalar Fraction reference. Does not import the reducer or NumPy.

Uses exact binary values from supplied floating point RGB input and eta. This is
separate arithmetic code by the same executor, not independent scientific review.
"""
from fractions import Fraction


def reference(fields):
    result = []
    batch, time, height, width, channels = fields["d_a"].shape
    # Specify coefficients independently (spatial offsets relative to centre).
    stencils = {
        "identity": [(0, 0, 1, 1)],
        "laplacian": [(-1, 0, 1, 4), (0, -1, 1, 4), (0, 0, -4, 4), (0, 1, 1, 4), (1, 0, 1, 4)],
        "sobel_x": [(-1, -1, -1, 8), (-1, 1, 1, 8), (0, -1, -2, 8), (0, 1, 2, 8), (1, -1, -1, 8), (1, 1, 1, 8)],
        "sobel_y": [(-1, -1, -1, 8), (-1, 0, -2, 8), (-1, 1, -1, 8), (1, -1, 1, 8), (1, 0, 2, 8), (1, 1, 1, 8)],
    }
    eta = Fraction.from_float(1e-12)
    for bi in range(batch):
        # Conversion to Fractions uses binary floats, never decimal rounding.
        cache = {k: {} for k in fields}
        for k, a in fields.items():
            for t in range(time):
                for y in range(height):
                    for x in range(width):
                        for c in range(channels):
                            cache[k][t, y, x, c] = Fraction.from_float(float(a[bi, t, y, x, c]))
        rows = []
        for name, stencil in stencils.items():
            sums = {k: Fraction(0) for k in ("K2", "S2", "SK", "Va2", "Vb2", "AB")}
            count = 0
            for t in range(time):
                for y in range(1, height - 1):
                    for x in range(1, width - 1):
                        for c in range(channels):
                            filt = {}
                            for key in fields:
                                filt[key] = sum((cache[key][t, y + dy, x + dx, c] * Fraction(n, den)
                                                for dy, dx, n, den in stencil), Fraction(0))
                            # Exact rational linearity, independent of vectorized operations.
                            k = filt["d_a"] - filt["d_b"]
                            s = filt["d_a"] + filt["d_b"]
                            sums["K2"] += k * k
                            sums["S2"] += s * s
                            sums["SK"] += s * k
                            sums["Va2"] += filt["v_a"] ** 2
                            sums["Vb2"] += filt["v_b"] ** 2
                            sums["AB"] += filt["d_a"] * filt["d_b"]
                            count += 1
            denominator = (sums["Va2"] + sums["Vb2"]) / count + eta
            q = sums["K2"] / count / denominator
            r = [sums["S2"] / count / denominator, q, sums["SK"] / count / denominator]
            rows.append({"filter": name, "elements": count, "sums": {k: str(v) for k, v in sums.items()},
                         "Dmean": str(denominator), "q": str(q), "r": [str(v) for v in r]})
        result.append({"sample_index": bi, "filters": rows})
    return result
