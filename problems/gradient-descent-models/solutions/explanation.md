# Gradient Descent Models: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| batch-gradient-descent | optimal | O(s n d) per training run | O(n d) | default answer |

`n` is the number of examples, `d` the number of features and `s` the number of steps. Cross-validation runs `k` trainings per strength, and `chooseStrength` one cross-validation per strength.

## How the design grows level by level

| Level | Adds | Reuses |
|-------|------|--------|
| 1 | The prediction `z`, the MSE and its gradient, one training loop that records rows | |
| 2 | The sigmoid, the clipped log loss and its gradient | The training loop, with another loss and gradient |
| 3 | The penalty and its slope, fold bounds, a fresh training per fold | The MSE and its gradient on any list of examples |
| 4 | The scaler, a standardized copy of the table, the early stopping loop, the correlation and a one-feature model | The MSE gradient step of level 1, on the standardized training part |

The one decision that keeps the later levels short is made at level 1: the MSE and its gradient take the examples and labels as arguments instead of reading the whole table. A fold, a training part or a standardized copy is then just another list to pass in.

## Approach: batch-gradient-descent (Full-batch gradient steps shared by every model with folds and splits around them)

### Intuition

Gradient descent is walking downhill in fog. You cannot see the lowest point of the loss, but you can feel the slope under your feet, so you take a step against it and feel again. The gradient is that slope, one number per weight, and the learning rate is the length of the stride. A stride that is too long carries you across the valley and up the other side, higher each time: that is the divergence of level 1's second example.

Every model here is the same walk on a different hill. Linear regression measures squared misses. Logistic regression squeezes `z` into a probability and charges `-ln` of the probability given to the right answer, which is the negative log-likelihood of the labels: the model is rewarded for giving high probability to what actually happened. Its gradient comes out as `(p - y) * x`, the same shape as linear regression's `(z - y) * x` without the 2, so one training loop serves both.

The last two levels are about the gap between the hill you can see and the one you care about. The training loss is computed on examples the model has already seen; what matters is the loss on the next example. A model with enough freedom can drive the first down by learning noise, which pushes the second up. Two brakes help: a penalty that makes large weights expensive (level 3), and stopping before the noise is learned (level 4). Both have a knob, a strength or a number of steps, and the knob must be set using examples the model did not train on, or the measurement is fooled by the very thing it is meant to catch. Leakage breaks the same rule more quietly, and the two leaks of level 4 behave differently. A scaler fitted on all the examples lets the validation features shape every training step. They carry no label, and for a linear model a scaler only changes the units, so the leak changes the path and moves the validation error up or down with no reliable direction: the number is no longer a clean measurement, but it is not reliably flattered either. A choice made with the validation labels in view is different: it rewards whatever matches those labels, chance included, so it flatters the score. In a quick simulation on 2,000 random tables of 10 examples, 3 of them set aside, with 4 features of random whole numbers and labels that are pure noise, choosing the feature on every example changed the choice in 835 tables and lowered the reported validation error in 96% of those. On 2,000 random tables like level 4's flats, the leaky scaler gave a lower error in only about a third of them.

### Algorithm

1. `predict(row, weights)`: start from the bias and add `wj * xj` in feature order.
2. `mse(examples, labels, weights)` and `mseGradient(...)`: one loop computes each miss `z - y`, squares it for the loss, and adds `miss` and `miss * xj` to the gradient sums, which are multiplied by `2 / n` at the end.
3. `train(loss, gradient, rate, steps)`: from the zero weights, record a row, then `steps` times compute the gradient, build the new weights `w - rate * g` all at once, and record a row. Rounding happens only when a row is recorded.
4. Logistic regression passes the log loss, which clips `p` to `[10^-7, 1 - 10^-7]` before `ln`, and the gradient `(1 / n) * sum of (p - y) * x` with the unclipped `p`.
5. Ridge passes `mse + strength * sum of wj^2` and a gradient with `2 * strength * wj` added to every slope but the bias's.
6. Cross-validation computes fold bounds (`n // k` each, one more for the first `n % k`), and for each fold trains a fresh model on the examples outside it, then records the MSE inside and outside. The last row is the plain mean of each column. `chooseStrength` keeps the strength with the lowest rounded mean validation error, replacing it only on a strictly lower one.
7. The scaler takes each column's mean and population standard deviation over the rows it is given, with 1 for a deviation of 0. Early stopping standardizes a copy of the whole table, splits it, and runs level 1's step on the training part, rounding each validation error, keeping the best step's weights, and stopping on `maxSteps` or `patience`. The leakage check runs the same function with the scaler fitted on every row.
8. The correlation of a column with the labels is `sum of dx * dy / sqrt(sum of dx^2 * sum of dy^2)`, the `d` being differences from the means, and 0 when either sum of squares is 0. The selection check rounds the size of each feature's correlation, keeps the first largest, once over the training part and once over every row, and for each choice standardizes that one column with the training part's mean and scale and trains a two-weight model on the training part.

### Correctness

**The gradients.** For one example the MSE term is `(z - y)^2`, and `z` grows by exactly `xj` when `wj` grows by one (by 1 for the bias), so its slope is `2 (z - y) xj`; averaging over the examples gives the formulas of level 1. For the log loss, the slope of the sigmoid is `p (1 - p)`. For a label 1 the loss is `-ln p`, whose slope in `z` is `-(1 / p) * p (1 - p) = p - 1`; for a label 0 it is `-ln(1 - p)`, whose slope is `(1 / (1 - p)) * p (1 - p) = p`. Both are `p - y`, which gives level 2's formulas with no factor 2. The penalty `strength * wj^2` has slope `2 * strength * wj` and does not involve the bias.

**The clipping.** Clipping keeps `ln` away from 0, so the loss is finite. The gradient deliberately uses the unclipped `p`: the slope of the clipped loss is 0 wherever the clip is active, which would leave a confidently wrong model with no signal to improve, the case where it is needed most. Example 2 of level 2 shows the gradient still pointing the right way at `[-60, 40]`.

**Why the steps behave as they do.** The MSE is a bowl whose curvature does not change: if `H` is its matrix of second slopes (here `(2 / n)` times the sum of `x x^T` over the examples, the bias's `x` being 1), then one step multiplies the distance to the bottom along each of `H`'s main directions by `1 - rate * curvature`. In level 1's second example the largest curvature is about 24.72, so a rate of 0.1 multiplies that distance by about `-1.47` per step: it overshoots, and the loss grows by about `1.47^2`, which is the factor of a little over 2 seen in the rows. Any rate above `2 / 24.72`, about 0.081, diverges there. Standardizing gives each feature, taken alone, a curvature of 2, and removes the coupling between the bias and the weights; correlated features still pull on each other through the entries of `H` off its diagonal. In level 4's first example there is one standardized feature that varies (the other is constant, so its weight never moves), `H` is exactly 2 times the identity, and a rate of 0.25 closes exactly half of the distance at every step.

**Folds, splits and leakage.** Every training run starts from the zero weights and reads only the examples passed to it, so a fold's validation examples, or the validation part, never reach its gradient. The only paths from them into the model are statistics computed over them, which is exactly what the two checks turn on: the leaky scaler reads their features, and the leaky selection their labels. When the leaky selection's choice differs from the honest one, the honest choice was at least as strong over the training part, so the leaky choice can only have taken the lead once the validation examples were counted. It tends to be the feature that happens to fit the validation labels, which is why its error almost always comes out lower.

### Complexity

- Time: O(s n d) per training run — each step computes `n` predictions of `d` terms and adds `n (d + 1)` products to the gradient; rounding a row costs `d`. A cross-validation is `k` runs on about `n (k - 1) / k` examples, and `chooseStrength` repeats it per strength.
- Space: O(n d) — the copy of the table and, at level 4, its standardized copy; a training run keeps one weight vector, and the rows it returns take `s d`.

### Trade-offs

Batch gradient descent reads every example per step. That makes each step exact and the whole run reproducible, which this problem needs, but it is slow on large tables, where a step on a small random batch is far cheaper and noisy in a way that often helps. Linear and ridge regression also have closed-form solutions: the bottom of the ridge bowl solves `(X^T X + n * strength * I') w = X^T y`, where `I'` is the identity with a 0 for the bias, which is the "small positive quantities added to the diagonal" of the further reading. Solving it is exact and fast for a few features; gradient descent wins when there are many features. Logistic regression has no closed form, so it needs an iterative method; gradient descent is the simplest.

The penalty and early stopping are two brakes with a similar effect. For a linear model with squared error trained by plain gradient descent from zero, stopping early behaves like an L2 penalty whose strength shrinks as the number of steps grows (see the further reading). The penalty gives a model that does not depend on how long you train; early stopping costs nothing extra, since the validation error is computed anyway.

Cross-validation uses every example for validation once, which matters on small tables, at the price of `k` trainings. A single validation split is `k` times cheaper and noisier. And whichever is used to choose a strength or a step, the chosen error is optimistic, because it was the best of several: a final, untouched test set is the honest measure.

### Pitfalls and edge cases

- **Forgetting the 2, or copying it.** The MSE's gradient has a factor 2 and the log loss's has none (`h1`, `h5`).
- **Updating weights one at a time.** Each slope must come from the weights before the step; moving the bias first and then computing the next slope with the new bias is a different algorithm (`h3`).
- **The starting row.** `steps` steps give `steps + 1` rows, starting with the zero weights, and each row's loss is at that row's weights (`h2`).
- **Rounding.** Round to the nearest 6-decimal value, and only what is returned: rounding the weights between steps changes the path (`h3`, `h5`), and cutting the digits is not rounding (`h1`).
- **The wrong logarithm or no clipping.** The log loss uses the natural logarithm, and a confidently wrong example costs exactly `-ln(10^-7)`, not 20 or 34.5 (`h6`).
- **Penalizing the bias.** It shifts every prediction and cannot overfit; penalizing it pulls the predictions toward 0 for nothing (`h8`).
- **The ridge rows.** Their loss includes the penalty; the cross-validation errors do not (`h8`, `h9`).
- **Fold boundaries.** Consecutive blocks, the larger ones first: with 7 examples and 3 folds, examples 0 to 2, 3 to 4, 5 to 6. Dealing examples out by remainder, or giving the extra examples to the last folds, measures something else (`h9`).
- **The mean over folds.** Each fold counts once, whatever its size (`h9`).
- **Training each fold from scratch.** Starting a fold from the previous fold's weights lets it learn from examples it is about to be tested on (`h10`).
- **Choosing on training error.** The training error always prefers no penalty; only the validation error can show that a penalty helps (`h12`). A tie keeps the first strength listed (`h11`).
- **Population standard deviation.** Divide by `m`, not `m - 1`, and use 1 for a feature that does not vary, so nothing is divided by 0 (`h13`, `h16`).
- **The scaler's rows.** Fitted on the training part only, which is the first `n - validationCount` examples (`h13`, `h14`, `h16`).
- **The scaler's leak has no direction.** Fitting the scaler on every example can raise or lower the validation error (`ex8`, `h16`, `h17`): the point is that the number no longer measures unseen data, not that it is always flattered.
- **The size of the correlation, not its sign or the covariance.** A strong negative correlation predicts as well as a strong positive one, and a covariance grows with a feature's units (`h19`, `h20`). A feature that does not vary has a correlation of 0, not a division by 0, and a tie goes to the lower index (`h19`).
- **The honest choice reads the training labels only.** Choosing over every example in the honest run too hides the leak (`h20`).
- **The best weights, not the last.** Early stopping returns the weights of the best step (`h15`).
- **Patience.** Stop as soon as `patience` steps in a row brought no new best: with patience 1, the first step that is not better ends training (`h15`).
- **Equal is not better.** An error equal to the best, after rounding, is not a new best; and comparing unrounded errors would let tiny changes in the last digits keep training going forever on a flat stretch (`h18`).
- **A diverging rate.** The loss grows and the weights swing; nothing in the code is wrong, and the fix is a smaller rate (`ex2`).

### Language notes

- Python: `sum` of floats has used a more accurate summation algorithm since Python 3.12, so it can differ in the last bit from a plain loop or from TypeScript's `reduce`. The tests do not depend on that, but the Python reference adds with plain loops so that both references return the very same doubles. `math.exp` raises `OverflowError` above about 709 and `math.log(0)` raises `ValueError`, where TypeScript returns `Infinity` and `-Infinity`: clipping, and the bound on `z` in the tests, keep both away.
- TypeScript: `new Array<number>(n).fill(0)` is needed for the gradient sums, since unfilled entries are holes that turn every sum into `NaN`. The constructor copies its arrays into fields declared on the class, so a caller who changes its arrays later cannot change the model. `Math.floor(x * 1_000_000 + 0.5) / 1_000_000` rounds exactly as the Python reference does.
- Both: the linear levels use only addition, subtraction, multiplication, division and `sqrt`, which IEEE 754 requires to be correctly rounded, so the two references agree bit for bit even before rounding. `exp` and `log` carry no such requirement, and Python's and Node's libraries differ in the last bit for some inputs; that is why every result is rounded to 6 decimals and the tests keep their values far from a halfway point.

## Further reading

- I. Goodfellow, Y. Bengio and A. Courville, [Deep Learning](https://www.deeplearningbook.org/), MIT Press, 2016: gradient-based optimization (section 4.3); capacity, overfitting and underfitting (5.2); validation sets and k-fold cross-validation (5.3 and algorithm 5.1); logistic regression, which has no closed-form solution and is trained by minimizing the negative log-likelihood with gradient descent (5.7.1); penalties that leave the biases unregularized (7.1) and L2 regularization (7.1.1); and early stopping with a patience counter that returns the best parameters, with the result that for a linear model with squared error and plain gradient descent it is equivalent to L2 regularization (7.8 and algorithm 7.1).
- A. E. Hoerl and R. W. Kennard, "Ridge Regression: Biased Estimation for Nonorthogonal Problems", Technometrics 12(1):55-67, 1970, doi:10.1080/00401706.1970.10488634: least-squares estimates can be badly off when the features are correlated, and adding small positive quantities to the diagonal of `X^T X` gives biased estimates with a smaller mean squared error.
- S. Kaufman, S. Rosset, C. Perlich and O. Stitelman, "Leakage in data mining: Formulation, detection, and avoidance", ACM Transactions on Knowledge Discovery from Data 6(4):1-21, 2012, doi:10.1145/2382577.2382579: leakage as information about the target that should not legitimately be available when learning, avoided by separating what is learned from what is predicted, with ways to detect it.
- [scikit-learn, Common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html): preprocessing must be learned from the training data only, "never call `fit` on the test data", and an example in which selecting features on all the data makes random labels look predictable.
- [scikit-learn, `StandardScaler`](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html): `(x - u) / s` with the biased standard deviation (`ddof=0`), and a scale of 1 for a feature whose variance is 0.
- [scikit-learn, `KFold`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.KFold.html): consecutive folds without shuffling, the first `n_samples % n_splits` of them one sample larger.
- [scikit-learn, `log_loss`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.log_loss.html): the log loss as the negative log-likelihood of a logistic model, with probabilities clipped to `[eps, 1 - eps]`; there `eps` is the machine precision of the input's type, not this problem's `10^-7`.
