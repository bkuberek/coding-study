# Gradient Descent Models

## Statement

Build `LinearModels`, which learns from a small table of data by **gradient descent**, the procedure behind most of machine learning, and then checks honestly how well what it learned would do on data it has not seen. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working.

**Examples, features and labels.** The data is a table of `n` **examples**. Each example has `d` numbers that describe it, its **features** (for a flat: its area, its number of rooms, its age), and the number a model should learn to produce for it, its **label** (the flat's price). The constructor receives the features as `n` rows of `d` numbers and the labels as `targets`. They never change.

**Weights and predictions.** A model here holds `d + 1` numbers, its **weights**, always listed as `[b, w1, ..., wd]`. `b` is the **bias**, the starting point when every feature is 0, and `wj` says how much feature `j` moves the result. For an example with features `x1, ..., xd` the model computes

```text
z = b + w1 * x1 + w2 * x2 + ... + wd * xd
```

added in exactly that order. `z`, or a number computed from it, is the model's **prediction** for the example. Learning means finding weights whose predictions are close to the labels.

**Loss and gradient.** The **loss** is one number that says how wrong the predictions are over the whole table: 0 when they are perfect, larger when they are worse. The **gradient** is a list of `d + 1` slopes, one per weight: how fast the loss grows when that weight grows a tiny bit and the others stay put. A negative slope says "raise this weight to lower the loss", a positive one "lower it", and a slope near 0 says the weight is about right.

**Gradient descent.** Start with every weight at 0. One **step** computes the gradient at the current weights from all the examples at once, then moves every weight against its slope:

```text
weight = weight - learningRate * slope
```

All weights move together, from the gradient computed before any of them moved. The **learning rate** sets the size of the step: too small and learning crawls, too large and every step overshoots, so the loss grows instead of shrinking.

**Training rows.** A method that trains returns one row per state of the weights: the zero weights first, then the weights after each step. A row is `[loss, b, w1, ..., wd]`, the loss being the one at that row's weights, so `steps` steps give `steps + 1` rows.

**Numbers.** Every number a method returns is rounded to 6 decimal places, a value exactly halfway going up, toward positive infinity (`0.0000005` becomes `0.000001`). Step counts are whole numbers and need no rounding. Rounding happens only to what is returned, and where a level says to compare rounded values: the weights themselves are never rounded between steps. The tests keep every number they check far from a halfway value, so any correct way of rounding to 6 places, and any order of adding up a sum, gives the same answer.

Aim to finish in 90 minutes. A good split: finish level 1 by minute 20, level 2 by 35, level 3 by 60 and level 4 by 85.

## Input

- `LinearModels(features, targets)`: the table. `features[i]` holds the `d` features of example `i`, and `targets[i]` its label.
- `weights`: `d + 1` numbers, the bias first.
- `learningRate`: the size of a step. `steps`: how many steps to take, from the zero weights.
- Each level's section describes the methods it adds.

## Output

Numbers rounded to 6 decimal places as described above, and rows as each method describes. Numbers are compared with a tolerance of `10^-9`, far below the last rounded digit.

## Level 1: Linear regression

The prediction is `z` itself, a number on the same scale as the labels. The loss is the **mean squared error** (MSE), the average of the squared differences between prediction and label:

```text
MSE = (1 / n) * sum over the examples of (z - y)^2
```

where `y` is the example's label. Squaring makes every miss count as positive and big misses count much more than small ones. Its gradient comes from the rule that the slope of `e^2` is `2e`:

```text
slope of b  = (2 / n) * sum of (z - y)
slope of wj = (2 / n) * sum of (z - y) * xj
```

The bias acts like a weight whose feature is always 1.

- `linearLoss(weights)`: the MSE of the given weights.
- `linearGradient(weights)`: the gradient of the MSE at the given weights, `[slope of b, slope of w1, ...]`.
- `trainLinear(learningRate, steps)`: gradient descent on the MSE from the zero weights, as training rows.

### Example 1

<!-- case: ex1 -->

Two examples: feature 1 with label 3, and feature 2 with label 5. The line `3 = 1 + 2 * 1`, `5 = 1 + 2 * 2` fits both, so the weights `[1, 2]` have loss 0. At the zero weights both predictions are 0, the misses are `-3` and `-5`, and the loss is `(9 + 25) / 2 = 17`. The slope of `b` is `(2 / 2) * (-3 - 5) = -8`, and the slope of `w1` is `(2 / 2) * (-3 * 1 - 5 * 2) = -13`. Both are negative, so both weights go up. With a learning rate of 0.1, one step gives `b = 0 - 0.1 * (-8) = 0.8` and `w1 = 1.3`. The predictions are now 2.1 and 3.4, the misses `-0.9` and `-1.6`, and the loss `(0.81 + 2.56) / 2 = 1.685`. Two more steps bring it to 0.16925 and then 0.019169, as the weights close in on `[1, 2]`.

### Example 2

<!-- case: ex2 -->

Two features this time, and labels that follow `1 + 1 * x1 + 2 * x2` exactly, so the gradient at `[1, 1, 2]` is all zeros: nothing there can be improved. From the zero weights, a learning rate of 0.02 brings the loss from 60.5 down to 0.773218 in four steps. A rate of 0.1 overshoots: the weights swing past the answer, each time further than the last, and the loss grows from 60.5 to 610.250362. That is divergence, and the only cure is a smaller step.

## Level 2: Logistic regression

Now the labels are 0 or 1: no or yes, like "this email is spam". The prediction is a **probability** between 0 and 1, made from `z` by the **sigmoid** function:

```text
p = 1 / (1 + e^(-z))
```

A large positive `z` gives a `p` close to 1, a large negative one a `p` close to 0, and `z = 0` gives 0.5. To answer yes or no, you compare `p` with a **threshold** such as 0.5, but this level trains and measures the probabilities themselves.

The loss is the **log loss**, the mean over the examples of

```text
-ln(p)       for an example with label 1
-ln(1 - p)   for an example with label 0
```

where `ln` is the natural logarithm. A confident right answer costs almost nothing, and a confident wrong one costs a lot: `-ln(0.01)` is about 4.6. As `p` reaches 0 or 1, `ln` would reach minus infinity, so before taking the logarithm `p` is **clipped** to the range from `ε` to `1 - ε`, with `ε = 10^-7`: `p = min(max(p, ε), 1 - ε)`, and `1 - p` is then computed from that clipped `p`. A single example therefore costs at most about 16.118.

The gradient of the log loss works out to a simple form, with no factor 2, and it uses the probability before clipping:

```text
slope of b  = (1 / n) * sum of (p - y)
slope of wj = (1 / n) * sum of (p - y) * xj
```

- `logisticLoss(weights)`: the log loss of the given weights.
- `logisticGradient(weights)`: the gradient of the log loss at the given weights.
- `trainLogistic(learningRate, steps)`: gradient descent on the log loss from the zero weights, as training rows whose loss is the log loss.

### Example 1

<!-- case: ex3 -->

At the zero weights every `z` is 0 and every `p` is 0.5, so each example costs `-ln(0.5) = ln(2) = 0.693147`, and so does the mean. The `p - y` terms are `0.5, -0.5, 0.5, -0.5`, which cancel for the bias, while for `w1` they give `(0.5 * 1 - 0.5 * 2 + 0.5 * 3 - 0.5 * 4) / 4 = -0.25`. The labels alternate, so no single weight separates them well, and training lowers the loss only slowly.

### Example 2

<!-- case: ex4 -->

The weights `[-6, 4]` give `z = -2` for the first example (label 1) and `z = 2` for the second (label 0): `p` is 0.119203 and 0.880797, wrong both times, and each costs 2.126928. With `[-60, 40]`, `z` is `-20` and `20`, and the model is sure and wrong. Without clipping each example would cost about 20; clipped, each costs `-ln(10^-7) = 16.118096`. The gradient uses the unclipped `p`: `p - y` is about `-1` and `1`, so the slope of `b` is 0 and the slope of `w1` is `(-1 * 1 + 1 * 2) / 2 = 0.5`.

## Level 3: Regularization and cross-validation

A model with many weights and few examples can **overfit**: it bends to follow the accidents of its training examples, the noise, and then predicts new examples worse than a simpler model would. The training loss alone cannot show this, because it keeps falling. This level adds a brake, a **penalty** on large weights, and a fair way to measure on unseen examples, **cross-validation**, which chooses how hard to brake.

**The penalty.** Training minimizes `MSE + strength * (w1^2 + ... + wd^2)`, where `strength` is 0 or more. The bias is not penalized: it only shifts every prediction and cannot bend the model. The penalty adds `2 * strength * wj` to the slope of each `wj` and nothing to the slope of `b`. This is called L2 regularization, and linear regression trained this way is called ridge regression.

**Folds.** `k`-fold cross-validation splits the examples, in their order, into `k` blocks of consecutive examples called **folds**. Each fold has `n / k` examples rounded down, and the first `n mod k` folds have one more. For each fold in turn, a model is trained **from the zero weights** on all the other examples, for `steps` steps of gradient descent with the penalty, and then measured: its **training error** is the plain MSE (no penalty) on the examples it trained on, and its **validation error** the plain MSE on the fold it never saw.

- `trainRidge(learningRate, steps, strength)`: gradient descent with the penalty, from the zero weights, on all the examples, as training rows whose loss is `MSE + penalty`.
- `crossValidate(learningRate, steps, strength, folds)`: one row `[training error, validation error]` per fold, in fold order, then a last row with the plain means of the two columns over the folds, each fold counting once whatever its size.
- `chooseStrength(learningRate, steps, strengths, folds)`: cross-validates every strength of `strengths` and returns `[strength, mean validation error]` for the one with the lowest mean validation error, compared after rounding. When several are lowest, the first in the list wins.

### Example 1

<!-- case: ex5 -->

The two examples of level 1, with strength 0.5. At the zero weights the penalty has no slope, so the first step is the one of level 1, to `[0.8, 1.3]`, but its loss now adds `0.5 * 1.3^2 = 0.845` to the MSE of 1.685: 2.53. On the second step the MSE slopes are `-2.5` and `-4.1`, and the penalty adds `2 * 0.5 * 1.3 = 1.3` to the second: `-2.8`. So `w1` grows only to 1.58 instead of 1.71, while `b` reaches 1.05 as before. Then two folds of one example each: fold 0 trains on `(2, 5)` and reaches `[1, 1.8]`, which predicts 4.6 for its training example (error 0.16) and 2.8 for the label 3 it never saw (error 0.04). Fold 1 trains on `(1, 3)`, reaches `[0.96, 0.9]`, and predicts 2.76 for the label 5 (error 5.0176). The last row averages the folds.

### Example 2

<!-- case: ex6 -->

The labels are a straight line, `1 + x`, plus some noise, but the features offer `x`, `x^2` and `x^3`, so the model can bend. Three folds of three. Without a penalty, the second fold's model fits its six training examples closely (training error 0.023983) and misses its own three badly (validation error 1.045348): it has learned the noise. On average the training error is 0.108773 and the validation error 0.574646. With strength 0.2 the training error rises to 0.283148 and the validation error falls to 0.38368: worse on what the model saw, better on what it did not. Of the six strengths tried, 0.2 has the lowest mean validation error.

## Level 4: Early stopping and leakage

**The validation split.** Here the last `validationCount` examples are set aside as the **validation part**, and the others, the first `n - validationCount`, are the **training part**. The model learns only from the training part.

**Standardization.** Features come on very different scales: an area in hundreds, a number of rooms below ten. A step that suits one is far too big or too small for the other. So each feature is first **standardized**: shifted by its mean and divided by its spread, so that every feature has mean 0 and spread 1. For each feature, the mean is the average of its values over the **training part only**, and the **scale** is its population standard deviation there, `sqrt(sum of (x - mean)^2 / m)` over the `m` training examples, or 1 when that is 0 (a feature that never changes is only shifted). Every example, training and validation alike, becomes `(x - mean) / scale` with these numbers.

**Early stopping.** As training goes on, the training error keeps falling, but past some step the model starts to learn the noise of the training part and the validation error climbs back up. Early stopping watches the validation error and keeps the best weights seen:

1. Standardize, then start from the zero weights.
2. Take one step of level 1's gradient descent (no penalty) on the standardized training part, then compute the validation error, the MSE on the standardized validation part, rounded to 6 decimals.
3. If this is the first step, or the rounded error is lower than the best so far, it becomes the best: remember the step, the error and the weights. Otherwise count one step without a new best; a new best resets that count to 0.
4. Stop after `maxSteps` steps, or as soon as `patience` steps in a row have brought no new best, whichever comes first. Otherwise go back to 2.

**Leakage.** The validation error measures how the model does on data it has never seen only if nothing about the validation examples went into it. So every step that is fitted on data, a scaler as much as the weights, is fitted on the training part only, and the validation part is used only to measure. Breaking that rule is called **leakage**, and it can happen in two ways:

- **Through the features.** A scaler fitted on all the examples takes its means and scales partly from the validation features. They carry no label, and for a linear model a scaler only changes the units, so the leak changes the path gradient descent takes and the step early stopping picks, and the validation error moves up or down, with no reliable direction. Either way it is no longer a clean measurement.
- **Through the labels.** A choice made by how well something fits the labels, with the validation labels in view, picks what happens to fit them, chance included, so the validation error comes out better than the model will do on new data. Here the choice is one feature. The **correlation** of a feature `x` with the labels `y` (Pearson's r) says how closely `y` follows a straight line in `x`, from `-1` (falling) through 0 (no line at all) to 1 (rising):

  ```text
  r = sum of (x - mean of x) * (y - mean of y) / sqrt(sum of (x - mean of x)^2 * sum of (y - mean of y)^2)
  ```

  over the examples considered, and `r = 0` when `x` or `y` does not vary there. The chosen feature is the one whose `r` is largest in size, `|r|`, compared after rounding to 6 decimals; a tie goes to the lower index.

- `fitScaler(validationCount)`: `[[means], [scales]]`, one entry per feature, fitted on the training part.
- `earlyStop(learningRate, maxSteps, patience, validationCount)`: `[best step, steps taken, training error at the best step, validation error at the best step, b, w1, ..., wd]`, the weights being those of the best step, in standardized units. Steps are counted from 1.
- `leakageCheck(learningRate, maxSteps, patience, validationCount)`: runs the early stopping twice, once as above and once with the scaler fitted on all `n` examples (everything else the same), and returns `[best step, validation error, leaky best step, leaky validation error]`.
- `featureCorrelations(validationCount)`: the `r` of each feature with the labels, over the training part.
- `selectionCheck(learningRate, steps, validationCount)`: chooses a feature twice, honestly over the training part and leakily over all `n` examples. For each choice it trains a model on that feature alone: the feature is standardized with its mean and scale over the training part, then `steps` steps of level 1's gradient descent run from `[0, 0]` on the training part. Returns `[chosen feature, validation error, leaky chosen feature, leaky validation error]`, a feature being its index in a row of `features`, from 0.

### Example 1

<!-- case: ex7 -->

With one example set aside, the training part's first feature is `1, 2, 3`: mean 2, and scale `sqrt((1 + 0 + 1) / 3) = 0.816497`. The second feature is always 5, so its scale is 1, every standardized value is 0 and its weight never moves. With two set aside, the first feature is `1, 2`: mean 1.5, scale 0.5. For early stopping, the training part follows `y = x`, so the model heads for a prediction of 4 for the validation example, whose label is 3. With standardized features and a learning rate of 0.25, each step here closes half of the remaining distance to the best fit, so the prediction goes 2, 3, 3.5, 3.75 and the validation error 1, 0, 0.25, 0.5625. Step 2 is the best, steps 3 and 4 bring nothing better, and with patience 2 training stops after step 4, returning the weights of step 2.

### Example 2

<!-- case: ex8 -->

Ten flats: area in square metres, rooms, and age in years, with prices as labels. The last three, set aside, are the largest, larger than any flat in the training part. The validation error falls to 0.130076 at step 4 and then rises at every step, while the training error keeps falling: the model gets better at the flats it sees and worse at new ones, so early stopping keeps step 4 and stops after step 7. Fitted on all ten flats, the scaler's mean area moves from 82.857143 to 101, and training takes another path: its best validation error is 0.072988, at step 20. It came out lower on this table, but on other tables the same leak makes it come out higher. What it changes for sure is the meaning of the number: the validation flats helped prepare the training, so the error no longer measures a model on flats it has never seen.

### Example 3

<!-- case: ex9 -->

Eight examples whose labels are whole numbers drawn at random, so no feature really predicts them. Over the five training examples, feature 0 has the correlation largest in size, `-0.836483`, so the honest run chooses it, and its model misses the three validation labels badly: an error of 13.858914. Over all eight examples, the validation labels included, feature 1 has a correlation of about 0.837 and feature 0 only about `-0.607`, so the leaky run chooses feature 1 and reports an error of 2.132041, more than six times better, on labels that are random. Feature 1 will not help with the next example: only the choice saw the answers.

## Constraints

- `1 <= n <= 20` examples and `1 <= d <= 4` features; every feature and label is between `-1000` and `1000`.
- `0 < learningRate <= 1`, `0 <= steps <= 500` and `1 <= maxSteps <= 500`.
- Level 2's labels are 0 or 1, and in its tests every `z` is between `-100` and `100`.
- `2 <= folds <= n`, `1 <= strengths.length <= 6`, and every strength is between 0 and 10.
- `1 <= validationCount <= n - 1` and `1 <= patience <= 50`.
- Every number stays finite in every test, even when a learning rate is too large.

## Follow-ups

- Each step here reads every example. With millions of examples, a step can read a small random batch instead (stochastic gradient descent). What changes in the results, and what would a test have to fix to stay exact?
- Linear regression also has a solution in closed form, by solving a linear system. When is gradient descent still the better choice?
- `chooseStrength` reports the validation error of the strength it picked, after looking at all of them. Is that number still an honest estimate for new data? How would nested cross-validation fix it?
- The folds here are consecutive blocks. What goes wrong when the table is sorted by label, or by date, and when is a split by date the right one?
- Scaling, choosing features and filling in missing values with an average are all steps fitted on data. How would you structure a pipeline so that every fitted step sees only the training part, including inside each fold of a cross-validation?

## Hints

### Hint 1

Start with something you can check by hand. A model here is a recipe: multiply each feature by a number, add them up with one more number, and that is the guess. The loss is the average of how far off the guesses are, squared. Write a function that computes the guess for one example, then use it to compute the loss for Example 1 with the weights `[0, 0]` and `[1, 2]`, and see 17 and 0.

### Hint 2

The slopes of the bias and of every weight come from the same loop over the examples: compute the miss `z - y` once per example, add it to the bias's sum, and add `miss * xj` to the sum of weight `j`. Scale the sums at the end.

### Hint 3

A training method is a loop of three lines: compute the gradient at the current weights, build the new weights from all the old ones and the gradient, and record a row. Build a new list of weights instead of updating the old one in place, so that no slope is computed from a weight that has already moved.

### Hint 4

Level 2 has the same shape as level 1, with a different prediction (`p` instead of `z`), a different per-example loss, and a gradient without the 2. If your training loop takes the loss and the gradient as functions, it serves both, and level 3's penalty too.

### Hint 5

For cross-validation, compute the start and end of each fold once, then for each fold build the training examples as everything before the start and everything after the end. Train a fresh model for each fold: reusing the weights of the previous fold lets it learn from the fold it is about to be tested on.

### Hint 6

For early stopping, keep four things besides the current weights: the best step, its rounded validation error, its weights, and how many steps have passed without a new best. For the leakage check, write the early stopping once, taking the scaler as an argument, and call it with the two scalers. The selection check works the same way: one function chooses a feature from the examples it is given, and you call it with the training part and with every example.

### Hint 7

The whole problem rests on two helpers that take the examples and labels as arguments: one returns the MSE, the other its gradient. Folds, splits and standardized copies are then just other lists of examples passed to the same helpers, and every training method is the same loop: `weights = [w - learningRate * g for w, g in zip(weights, gradient(weights))]`, starting from zeros, for `steps` steps.
