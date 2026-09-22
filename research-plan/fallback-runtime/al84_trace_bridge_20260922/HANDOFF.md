# AL84 handoff — bounded precomputed identity bridge

The fallback CPU package binds four archived OR1-style call records by sample, stage, probe, role, support layout, time slots, shape and tensor hashes. The canonical roles are `Ra_x`, `Rb_x`, `Ra_Pb`, and `Rb_Pa`; no model, decoder, media or network call is made.

For the AL15 contract, `Pa=(1-h)x+hRa(x)` and `Pb=(1-h)x+hRb(x)`. The bridge computes `v_a=Ra(x)-x`, `v_b=Rb(x)-x`, `d_a=(Ra(Pb)-Pb-Ra(x)+x)/h`, and `d_b=(Rb(Pa)-Pa-Rb(x)+x)/h`. It checks `d_a-d_b=(u_ab-u_ba)/h^2` before returning `d_a,d_b,v_a,v_b` for the read-only AL79 reducer.

After one pre-run path-resolution failure (`run_v0_startup_error.json`), v2 source/config/input hashes were frozen and one valid batch ran. The valid fields matched a separate arithmetic reference; eight malformed identity cases were rejected; one bounded RGB call to the existing AL79 reducer returned `rgb-reducer-v2`. This is a software/mock contract result only. The fixture does not authenticate a real probe, pixel correspondence, decoder, source label, model, or detection effect.

Resource receipt: network/media/server/models/GPU all zero; no independent scientific review. AL15 and AL79 remain scoped software passes; formal mechanism, real data, efficacy and innovation gates remain closed. Preserve the startup failure and v2 freeze; do not treat this handoff as a real OR1 experiment.
