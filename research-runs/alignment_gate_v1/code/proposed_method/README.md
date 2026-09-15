# Alignment-aware nuisance-adversarial prototype

`AlignmentNuisanceAdversarial` consumes aligned temporal features, predicts the
fake label, and predicts observable mask statistics through a gradient-reversal
branch. Training minimizes fake BCE plus nuisance MSE; the reversed gradient
discourages mask information in the shared representation.

This is the first executable method implementation derived from the gates. It
has only passed shape/gradient tests (`2 tests passed`); no performance claim is
made until fit/calibration/audit training and an independent real source are
available.
