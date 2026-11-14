# Linear and logistic regression

## The idea

A **linear model** predicts from the features with a weighted sum. Each feature `x1, ..., xd` gets a **weight** `w1, ..., wd`, and one more number, the **bias** `b`, is the starting point when every feature is 0:

```text
z = b + w1 * x1 + w2 * x2 + ... + wd * xd
```

A weight says how much its feature moves the result: a weight of 2.4 on the distance in kilometres means each extra kilometre adds 2.4 to `z`. Statisticians call the bias the **intercept** and the weights the **coefficients**; it is the same model. Training a linear model means choosing the weights and the bias, and two choices of what to do with `z` give the two models of this guide.

**Linear regression** predicts a number: the prediction is `z` itself. How wrong a set of weights is gets measured by a **loss**, one number for the whole training set that is 0 when every prediction is right and grows as they get worse. Linear regression uses the **mean squared error** (MSE):

```text
MSE = average over the examples of (prediction - label)^2
```

Each difference between prediction and label is a **residual**. Squaring makes every residual count as positive and big ones count much more than small ones. Finding the weights with the smallest MSE is called **least squares**, and for a linear model it has an exact answer, which the worked example computes.

**Logistic regression** answers a yes-or-no question with a probability. It squeezes `z` into the range from 0 to 1 with the **sigmoid** function:

```text
p = 1 / (1 + e^(-z))
```

A large positive `z` gives a `p` near 1, a large negative one a `p` near 0, and `z = 0` gives exactly 0.5. Read backwards, `z` is the **log odds** of `p`, `ln(p / (1 - p))`: the model is linear in the log odds, not in the probability. To answer yes or no you compare `p` with a **threshold**, often 0.5, which is the same as asking whether `z` is above 0. So the line, or with more features the flat surface, where `z = 0` separates the yes answers from the no answers: the model's **decision boundary** is linear.

Logistic regression is measured with the **log loss**, the average of `-ln` of the probability the model gave to what really happened:

```text
log loss = average of  -ln(p)      for an example labelled 1
                       -ln(1 - p)  for an example labelled 0
```

`ln` is the natural logarithm. A confident right answer costs almost nothing; a confident wrong answer costs a lot, without limit as the probability of the right answer goes to 0. It is the negative log-likelihood of the labels (how unlikely the model found what really happened), also called the **cross-entropy** between the data and the model, a name that covers any number of classes.

```mermaid
flowchart LR
  accTitle: From features to a yes or a no
  accDescr: The features are combined into a weighted sum z. Linear regression stops there. Logistic regression turns z into a probability with the sigmoid, and a threshold turns the probability into a yes or a no.
  x["features"] --> z["z = b + w * x"] --> p["p = sigmoid(z)"] --> y["yes when p >= 0.5"]
```

<!-- text-of-mermaid sha256:42aa21c4fed8daded7dab70efbb689defb33417828b451710c2fe7f553b2048a -->
```text
┌────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│features├───►│z = b + w * x├───►│p = sigmoid(z)├───►│yes when p >= 0.5│
└────────┘    └─────────────┘    └──────────────┘    └─────────────────┘
```

The drawing shows the chain. Linear regression stops at `z`; logistic regression goes on to a probability, and the threshold is a separate choice made after the model is trained.

## A worked example

### Fitting a line

Eight deliveries, each with its distance in kilometres and the minutes it took. The program fits a line by least squares, checks the answer against Python's `statistics.linear_regression`, and then moves the line a little in each direction to see that the MSE only goes up.

```python examples/fit_a_line.py
"""Fit a line by least squares, check it against the standard library, and see that it is the
lowest point of the mean squared error.

Each example is a delivery: its distance in kilometres (the feature) and how many minutes it took
(the label).
"""

import statistics

distances = [2, 4, 5, 7, 9, 12, 14, 15]
minutes = [18, 22, 27, 30, 35, 41, 47, 49]


def mse(slope: float, intercept: float) -> float:
    return statistics.fmean((slope * x + intercept - y) ** 2 for x, y in zip(distances, minutes))


# Least squares for one feature: the slope is how x and y vary together, over how x varies.
x_mean, y_mean = statistics.fmean(distances), statistics.fmean(minutes)
together = sum((x - x_mean) * (y - y_mean) for x, y in zip(distances, minutes))
alone = sum((x - x_mean) ** 2 for x in distances)
slope = together / alone
intercept = y_mean - slope * x_mean
print(f"by hand:          slope {slope:.4f}, intercept {intercept:.4f}")

library = statistics.linear_regression(distances, minutes)
print(f"by the library:   slope {library.slope:.4f}, intercept {library.intercept:.4f}")
print(f"10 km predicted:  {slope * 10 + intercept:.1f} minutes")

print(f"MSE of the fit:    {mse(slope, intercept):.3f}")
for name, (s, i) in {
    "slope + 0.2": (slope + 0.2, intercept),
    "slope - 0.2": (slope - 0.2, intercept),
    "intercept + 1": (slope, intercept + 1),
    "intercept - 1": (slope, intercept - 1),
}.items():
    label = f"{name}:"
    print(f"MSE, {label:<15}{mse(s, i):.3f}")
```

It prints:

```output examples/fit_a_line.py
by hand:          slope 2.3611, intercept 13.5556
by the library:   slope 2.3611, intercept 13.5556
10 km predicted:  37.2 minutes
MSE of the fit:    0.594
MSE, slope + 0.2:   4.294
MSE, slope - 0.2:   4.294
MSE, intercept + 1: 1.594
MSE, intercept - 1: 1.594
```

The line says a delivery takes about 13.6 minutes plus 2.36 minutes per kilometre. Every nudge raises the MSE, and by the same amount in both directions: the MSE of a linear model is a bowl, a **quadratic** function of the weights, and least squares finds its bottom. Moving the intercept by 1 adds exactly 1, because at the bottom the residuals average to zero, so shifting every prediction by 1 adds 1 to the average squared residual. Moving the slope by 0.2 adds 0.2² times the average of the squared distances, 92.5, which is 3.7.

With one feature the bottom has the closed form in the program. With many, it is the solution of a system of linear equations, as the expert notes say, and the next guide reaches the same bottom by walking downhill instead.

### Probabilities and their cost

The second program shows the sigmoid and its inverse, then compares the log loss with the squared error for an example whose right answer was given probability `p`.

```python examples/log_loss.py
"""The sigmoid turns any number into a probability, and the log loss charges for a probability
given to the wrong answer far more than the squared error does.
"""

import math


def sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z))


def log_odds(p: float) -> float:
    return math.log(p / (1 - p))


print("   z   p = sigmoid(z)   log odds of p")
for z in [-4, -2, 0, 2, 4]:
    print(f"{z:4}   {sigmoid(z):14.4f}   {log_odds(sigmoid(z)):13.1f}")

print()
print("p of the right answer   log loss   squared error")
for p in [0.99, 0.9, 0.7, 0.5, 0.3, 0.1, 0.01]:
    print(f"{p:20}   {-math.log(p):8.3f}   {(1 - p) ** 2:13.3f}")
```

It prints:

```output examples/log_loss.py
   z   p = sigmoid(z)   log odds of p
  -4           0.0180            -4.0
  -2           0.1192            -2.0
   0           0.5000             0.0
   2           0.8808             2.0
   4           0.9820             4.0

p of the right answer   log loss   squared error
                0.99      0.010           0.000
                 0.9      0.105           0.010
                 0.7      0.357           0.090
                 0.5      0.693           0.250
                 0.3      1.204           0.490
                 0.1      2.303           0.810
                0.01      4.605           0.980
```

The first table shows that the log odds undo the sigmoid, and that the sigmoid is symmetric: `z = 2` and `z = -2` give probabilities that add up to 1. The second shows why the log loss suits probabilities. The squared error of a probability can never exceed 1, so a model that is 99% sure of the wrong answer pays 0.98, hardly more than one that is 90% sure (0.81). The log loss charges 4.6 against 2.3: it keeps pushing a confidently wrong model, which is exactly the model that most needs to change. A coin flip, `p = 0.5`, costs `ln 2 = 0.693` per example, the number to beat.

## When to use it

- **Linear regression** when the label is a number and you want a baseline that is fast, exact and easy to read: each weight says what its feature adds.
- **Logistic regression** when the label is yes or no and you want a probability, not only an answer: to rank cases, to choose a threshold later, or to combine with costs.
- **Both as a baseline**, before anything more complex. A more complex model has to beat them on the validation set to earn its cost.
- **Not when the relationship bends** and the features cannot express the bend. A delivery that takes the same time up to 5 km and then grows needs a feature that captures it, such as the distance beyond 5 km, or a model that is not linear.
- **Not squared error for probabilities.** Training a probability with the MSE works poorly when training by gradient descent, the next guide's method, as the expert notes explain; use the log loss.

## Common traps

- **Reading weights as importance.** A weight depends on its feature's units: the same effect has a weight of 2.4 per kilometre and 0.0024 per metre. Compare weights only after putting the features on the same scale, and even then, two features that move together share their effect in ways that are hard to read.
- **Reading weights as causes.** A weight says how the prediction moves with a feature in this data, not what would happen if you changed the feature.
- **Treating the probability as a fact.** A logistic model's `p` is a probability only when the model is **calibrated**, which [classifier metrics](../classifier-metrics/guide.md) explains how to check.
- **Taking `ln(0)`.** A model that gives exactly 0 to the right answer has an infinite log loss; in CPython, `math.log(0.0)` raises `ValueError`. Implementations clip `p` a little away from 0 and 1 before taking the logarithm.
- **Computing the sigmoid of a large negative number naively.** `e^(-z)` overflows for `z` below about -709 in double precision, and CPython's `math.exp` raises `OverflowError`. For a negative `z`, `e^z / (1 + e^z)` gives the same value safely.
- **Extrapolating.** The line was fitted between 2 and 15 km. What it says about 60 km is a guess the data never checked.
- **Forgetting the bias.** A model without it must pass through 0: zero kilometres, zero minutes, which is rarely true.

## Complexity

For `n` examples with `d` features:

| Task | Time | Extra space |
|------|------|-------------|
| One prediction | O(d) | O(1) |
| The loss of a set of weights | O(n d) | O(1) |
| Least squares with one feature, as in the example | O(n) | O(1) |
| Least squares with `d` features, through the normal equations | O(n d²) to build them and O(d³) to solve them | O(d²) |
| Logistic regression | No closed form: an iterative method, each step costing O(n d) | O(d) |

## Expert notes

- **The normal equations.** In *The Elements of Statistical Learning* (§2.3.1), Hastie, Tibshirani and Friedman write the residual sum of squares as a quadratic function of the weights, whose minimum always exists but may not be unique. Setting its gradient to zero gives the **normal equations** `X^T (y - X w) = 0`, where `X` holds one row of features per example (with a 1 for the bias), `y` the labels, and `w` holds the bias and the weights; when `X^T X` can be inverted, the unique solution is `w = (X^T X)^(-1) X^T y`. They also note that the intercept is what machine learning calls the bias.
- **Why squared error, and why log loss.** Goodfellow, Bengio and Courville (*Deep Learning*, §5.5.1) show that if the labels are the model's prediction plus Gaussian noise, maximizing the likelihood of the data gives the same weights as minimizing the MSE. Logistic regression (§5.7.1) is the same idea for a yes-or-no label: a sigmoid turns the linear function into the probability of class 1, there is no closed-form solution, and the weights are found by minimizing the negative log-likelihood, which is the log loss, with gradient descent.
- **What a loss estimates.** With unlimited data, minimizing the squared error gives a function that predicts the mean of the label for each input, and minimizing the absolute error one that predicts the median (*Deep Learning*, §6.2.1.2). That is why the MSE is pulled hard by a few huge residuals and the absolute error is not.
- **Saturation.** The sigmoid flattens out toward 0 and 1. With the squared error, the gradient flattens with it, and becomes too small to learn from whether the answer is right or wrong; the log loss cancels the flattening, so maximum likelihood is almost always the preferred way to train a sigmoid output (*Deep Learning*, §6.2.2.2).
- **More than two classes.** The **softmax** generalizes the sigmoid to `n` classes: it turns `n` scores into `n` probabilities that add up to 1, and it does not change when the same number is added to every score, so implementations subtract the largest score first to avoid overflow (*Deep Learning*, §6.2.2.3).
- **Python's built-in fit.** `statistics.linear_regression`, added in Python 3.10, returns the slope and intercept of ordinary least squares for one feature. It needs at least two points and a feature that is not constant, and since Python 3.11 it accepts `proportional=True` to fit a line through the origin.

## Practice

- `cstudy start gradient-descent-models`: its first two levels compute the loss of linear and logistic regression for given weights, the slopes of that loss, and train both models from zero.

## Further reading

- [Hastie, Tibshirani and Friedman, *The Elements of Statistical Learning*, second edition](https://hastie.su.domains/ElemStatLearn/): §2.3.1, linear models and least squares.
- [Goodfellow, Bengio and Courville, *Deep Learning*, chapter 5](https://www.deeplearningbook.org/contents/ml.html): §5.5.1, the squared error as maximum likelihood; §5.7.1, logistic regression.
- [*Deep Learning*, chapter 6](https://www.deeplearningbook.org/contents/mlp.html): §6.2, cost functions, sigmoid and softmax outputs.
- [Python, `statistics.linear_regression`](https://docs.python.org/3/library/statistics.html#statistics.linear_regression): ordinary least squares for one feature.
- [Python, `math`](https://docs.python.org/3/library/math.html): `exp` and `log`, and the errors CPython raises when a result overflows or is undefined.
