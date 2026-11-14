# Review: the facts of the machine learning guides

The seven guides of the path "Machine learning fundamentals: from your first model to honest evaluation" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts from textbooks, papers and Python's documentation. This page lists each one with where it was checked, so that the independent review starts from the sources.

"Quote" means the exact text was read at that source: on the web page, or in the text extracted from the PDF with `pdftotext`. "Run" means an example of the guide, or a one-off program, printed it, on CPython 3.13.12. "Arithmetic" means the number was computed from the stated inputs. A fact that could not be checked was left out of the guides; the last sections list those, the citation choices, and where a guide comes close to a linked problem.

| Guide | Slug | Level |
|-------|------|-------|
| Data, features, splits and leakage | `data-splits-and-leakage` | intro |
| Linear and logistic regression | `linear-and-logistic-regression` | intro |
| Gradient descent and learning rates | `gradient-descent` | core |
| Overfitting, regularization and early stopping | `overfitting-and-regularization` | core |
| Cross-validation and choosing a model | `cross-validation` | core |
| Classifier metrics: from the confusion matrix to ROC and calibration | `classifier-metrics` | core |
| Evaluation pitfalls: when a good score is wrong | `evaluation-pitfalls` | advanced |

## The Elements of Statistical Learning

Hastie, Tibshirani and Friedman, *The Elements of Statistical Learning*, second edition, 12th printing, read in full from the PDF that the authors' [download page](https://hastie.su.domains/ElemStatLearn/download.html) links. Cited as ESL with its section numbers.

| # | Claim | Source |
|---|-------|--------|
| H1 | The intercept is also known as the bias in machine learning; least squares minimizes the residual sum of squares, a quadratic function of the parameters whose minimum always exists but may not be unique; differentiating gives the normal equations `X^T (y - X b) = 0`, with the unique solution `(X^T X)^(-1) X^T y` when `X^T X` is nonsingular | Quote: §2.3.1 (in `linear-and-logistic-regression`) |
| H2 | Ridge regression penalizes the sum of squared coefficients, shrinking them toward zero, and is known as weight decay in neural networks; with correlated variables a wildly large positive coefficient can be canceled by a similarly large negative coefficient on its correlated cousin, which a size constraint alleviates; the solutions are not equivariant under scaling, so inputs are normally standardized; the intercept is left out of the penalty, because penalizing it would make adding a constant to each target not simply shift the predictions by that constant; the solution adds a positive constant to the diagonal of `X^T X`, making the problem nonsingular even when `X^T X` is not of full rank, the main motivation when Hoerl and Kennard (1970) introduced it | Quote: §3.4.1 (in `overfitting-and-regularization`) |
| H3 | The lasso replaces the squared penalty by absolute values; there is no closed form; a small enough constraint makes some coefficients exactly zero, a kind of continuous subset selection; it was proposed by Tibshirani (1996) | Quote: §3.4.2 and the chapter's bibliographic notes (in `overfitting-and-regularization`) |
| H4 | Model selection estimates the performance of different models to choose one; model assessment estimates the chosen model's error on new data; in a data-rich situation the dataset is divided at random into training, validation and test sets; the test set should be kept "in a vault"; using it repeatedly to choose the model with the smallest test error makes the chosen model's test error underestimate the true one, sometimes substantially; a typical split is 50%, 25% and 25%, though no general rule fits every signal-to-noise ratio and sample size | Quote: §7.2 (in `data-splits-and-leakage`) |
| H5 | Expected squared error at a point is irreducible error plus squared bias plus variance; typically more complexity lowers the bias and raises the variance; for k-nearest neighbours the variance term is the noise variance over `k`, `k` is inversely related to complexity, a small `k` adapts better, and a larger `k` typically raises the bias while lowering the variance | Quote: §7.3, equations 7.9 and 7.10 (in `overfitting-and-regularization`) |
| H6 | K-fold cross-validation fits on `K - 1` parts and predicts the `k`-th; typical choices of K are 5 or 10; K = N is leave-one-out, approximately unbiased but with possibly high variance because the training sets are so similar, and requiring N fits; the final model with the chosen tuning parameter is fit to all the data; if the learning curve still has a considerable slope, five- or tenfold cross-validation overestimates the prediction error; five- or tenfold is recommended as a good compromise, citing Breiman and Spector (1992) and Kohavi (1995) | Quote: §7.10.1 (in `cross-validation`) |
| H7 | With 50 samples in two equal classes and 5,000 standard Gaussian predictors independent of the labels, the true error of any classifier is 50%; choosing the 100 predictors most correlated with the labels on all samples, then cross-validating a 1-nearest-neighbour classifier on them, gave an average cross-validation error of 3% over 50 simulations; the right way selects the predictors inside each fold, from the samples outside it | Quote: §7.10.2 (in `data-splits-and-leakage` and `cross-validation`) |
| H8 | The bootstrap draws datasets with replacement from the training data, each the size of the original, B times, and examines the behaviour of a quantity over the replications; it is due to Efron (1979); with B = 200 bootstrap samples, a 95% pointwise band is formed from the fifth largest and smallest values | Quote: §7.11, its bibliographic notes, and §8.2.1 (in `evaluation-pitfalls`) |
| H9 | The lasso penalty is somewhat indifferent to the choice among a set of strong but correlated variables, while the ridge penalty tends to shrink the coefficients of correlated variables toward each other | Quote: §18.4 (in `overfitting-and-regularization`) |

## Deep Learning

Goodfellow, Bengio and Courville, *Deep Learning*, MIT Press, 2016, read from the chapters on [deeplearningbook.org](https://www.deeplearningbook.org/): 4, 5, 6, 7, 8 and 11. Cited with its section numbers.

| # | Claim | Source |
|---|-------|--------|
| D1 | Underfitting is a training error that is not low enough; overfitting a gap between training and test error that is too large; capacity, the ability to fit a wide variety of functions, controls which is more likely; high-capacity models can overfit by memorizing properties of the training set | Quote: §5.2 (in `overfitting-and-regularization`) |
| D2 | Hyperparameters are settings not adapted by the learning algorithm; one that controls capacity cannot be learned on the training set, which would always choose the maximum capacity; test examples must not be used in any way to choose, so the validation set is built from the training data, typically 80% for training and 20% for validation; the validation error underestimates the generalization error, typically by less than the training error; a test set used repeatedly by a field for years gives optimistic evaluations, and benchmarks become stale | Quote: §5.3 (in `data-splits-and-leakage`, `overfitting-and-regularization` and `evaluation-pitfalls`) |
| D3 | For linear regression with Gaussian noise, maximizing the log-likelihood gives the same weights as minimizing the mean squared error: the two criteria have different values but the same location of the optimum | Quote: §5.5.1 (in `linear-and-logistic-regression`) |
| D4 | Logistic regression squashes a linear function into a probability with the logistic sigmoid; unlike linear regression it has no closed-form solution, and its weights are found by minimizing the negative log-likelihood with gradient descent | Quote: §5.7.1 (in `linear-and-logistic-regression`) |
| D5 | The negative log-likelihood is equivalently described as the cross-entropy between the training data and the model distribution; minimizing the squared error predicts the mean of y for each x, and the absolute error the median | Quote: §6.2.1.1 and §6.2.1.2 (in `linear-and-logistic-regression`) |
| D6 | With mean squared error, the loss can saturate whenever the sigmoid saturates, and the gradient can become too small to learn from whether the answer is right or wrong; maximum likelihood is almost always the preferred way to train sigmoid output units; mean squared and absolute error often lead to poor results with gradient-based optimization because saturating outputs give very small gradients | Quote: §6.2.2.2 and §6.2.1.2 (in `linear-and-logistic-regression`) |
| D7 | The softmax generalizes the sigmoid to a distribution over n values; it is invariant to adding the same scalar to all inputs, which gives the numerically stable variant that subtracts the largest input | Quote: §6.2.2.3 (in `linear-and-logistic-regression`) |
| D8 | Gradient descent, also called the method of steepest descent, proposes `x - ε ∇f(x)`, ε being the learning rate, often a small constant or chosen by a line search over several values | Quote: §4.3 (in `gradient-descent`) |
| D9 | When the curvature term is too large, a gradient step can move uphill; the optimal step along the gradient is `g^T g / g^T H g`, which is `1 / λmax` in the worst case, so the Hessian's eigenvalues determine the scale of the learning rate; a poor condition number makes gradient descent perform poorly and makes choosing a step size difficult | Quote: §4.3.1 (in `gradient-descent`) |
| D10 | Methods using the entire training set are batch or deterministic; those using one example at a time are stochastic or online; "batch size" usually means the size of a minibatch; minibatches must be selected randomly, since datasets are often arranged so that successive examples are correlated | Quote: §8.1.3 (in `gradient-descent`) |
| D11 | In practice the SGD learning rate must decrease over time, because the gradient estimate's noise does not vanish at a minimum; a sufficient condition for convergence is that the rates sum to infinity and their squares to a finite number; too large a rate gives violent oscillations, too low a rate slow learning that may get stuck; the computation per update does not grow with the number of training examples | Quote: §8.3.1 (in `gradient-descent`) |
| D12 | Momentum (Polyak, 1964) accumulates an exponentially decaying moving average of past gradients, to accelerate learning under high curvature and small, consistent or noisy gradients; it addresses poor conditioning of the Hessian and the variance of the stochastic gradient | Quote: §8.3.2 (in `gradient-descent`) |
| D13 | A common source of error is a wrongly implemented gradient; compare it with finite differences; the centered difference is more accurate; the perturbation must be large enough not to be rounded away | Quote: §11.5 (in `gradient-descent`) |
| D14 | Norm penalties usually penalize only the weights and leave the biases unregularized: a bias needs less data to fit, controls only a single variable, and regularizing it can introduce significant underfitting | Quote: §7.1 (in `overfitting-and-regularization`) |
| D15 | Training error often decreases steadily while validation error eventually rises again, reliably; early stopping stores the parameters at each improvement of the validation error, returns them, and ends when no improvement has come for a pre-specified number of iterations; for a linear model with a quadratic error and simple gradient descent it is equivalent to L2 regularization, the product of the number of steps and the learning rate behaving like the reciprocal of the weight decay coefficient | Quote: §7.8 (in `overfitting-and-regularization`) |
| D16 | In a convex optimization problem any local minimum is guaranteed to be a global minimum | Quote: §8.2.2 (in `gradient-descent`) |

## Leakage, cross-validation and model selection

Kapoor and Narayanan on [arXiv 2207.07048](https://arxiv.org/abs/2207.07048) (v1, 14 July 2022); Varma and Simon, *BMC Bioinformatics* 7:91, 2006, read from the open-access full text through Europe PMC (PMC1397873); Cawley and Talbot, *JMLR* 11:2079–2107, 2010; Bengio and Grandvalet, *JMLR* 5:1089–1105, 2004; Kohavi, IJCAI 1995, pages 1137–1143, from [ijcai.org](https://www.ijcai.org/Proceedings/95-2/Papers/016.pdf).

| # | Claim | Source |
|---|-------|--------|
| K1 | A survey of the literature found 17 fields where errors had been reported, collectively affecting 329 papers; the taxonomy has 8 types of leakage: lack of clean separation of training and test data (no test set, preprocessing on both, feature selection on both, duplicates); features that are not legitimate, such as a proxy for the outcome, with a study that used anti-hypertensive drugs as a feature to predict hypertension; and a test set not drawn from the distribution of scientific interest (temporal leakage, nonindependence such as the same patients on both sides, sampling bias); in civil war prediction, all papers claiming that complex models outperform logistic regression failed to reproduce because of leakage, and the complex models did not perform substantively better | Quote: abstract and §2.4 (in `data-splits-and-leakage` and `evaluation-pitfalls`) |
| K2 | Model info sheets ask, for each type of leakage, how training and test data were separated in preprocessing, feature selection and evaluation, whether there are duplicates, why each feature is legitimate, and why the test distribution matches the claim | Quote: abstract and appendix list L1.1 to L3.3 (in `evaluation-pitfalls`) |
| V1 | On "null" datasets with no difference between the classes, the cross-validation error of the classifier with optimal parameters was below 30% on 18.5% of datasets for Shrunken Centroids (10-fold) and 38% for SVM (leave-one-out), while on independent test data both were no better than chance; a nested procedure, an inner loop that tunes and an outer loop that estimates, gave an estimate very close to the independent test error | Quote: abstract (in `cross-validation`) |
| C1 | A low variance of a model selection criterion is at least as important as unbiasedness, since variance opens the way to over-fitting in model selection; its effects are often of comparable magnitude to differences between learning algorithms; some common evaluation practices are susceptible to selection bias and so unreliable | Quote: abstract (in `cross-validation` and `evaluation-pitfalls`) |
| G1 | There is no universal (valid under all distributions) unbiased estimator of the variance of K-fold cross-validation; naive estimators that ignore the error correlations due to overlapping training and test sets can grossly underestimate the variance | Quote: abstract (in `cross-validation`) |
| KO1 | In stratified cross-validation the folds contain approximately the same proportions of labels as the original dataset; repeating cross-validation with different splits gives a better Monte-Carlo estimate at added cost; from over half a million runs of two learning algorithms, for real-world datasets similar to theirs the best method for model selection is ten-fold stratified cross-validation, even if computation allows more folds | Quote: abstract and §2.2 (in `cross-validation`) |

## Reused test sets and adaptive analysis

Recht, Roelofs, Schmidt and Shankar on [arXiv 1902.10811](https://arxiv.org/abs/1902.10811) (v2, 12 June 2019); Dwork, Feldman, Hardt, Pitassi, Reingold and Roth on [arXiv 1411.2664](https://arxiv.org/abs/1411.2664) (v3, 2 March 2016; preliminary version at STOC 2015). Used in `evaluation-pitfalls`.

| # | Claim | Source |
|---|-------|--------|
| R1 | New test sets were built for two benchmarks by closely following the original dataset creation processes; accuracy dropped 3% to 15% on one and 11% to 14% on the other; the relative order of models was almost exactly preserved and gains on the original test sets translated to larger gains on the new ones; the drops are attributed not to adaptivity but to the models' inability to generalize to slightly harder images, a distribution shift arising from the reproduction | Quote: abstract, §1 and the discussion of robustness |
| DW1 | Statistical theory assumes hypotheses fixed before the data is gathered, while in practice analyses are chosen after earlier results; an exponential in `n` number of adaptively chosen expectations can be estimated accurately from `n` samples, against a linear number for standard empirical estimators, by perturbing the estimates with techniques developed for privacy preservation | Quote: abstract |

## Optimization and generalization

Bottou, Curtis and Nocedal on [arXiv 1606.04838](https://arxiv.org/abs/1606.04838) (v3, 8 February 2018); Kingma and Ba on [arXiv 1412.6980](https://arxiv.org/abs/1412.6980) (v9, 30 January 2017; ICLR 2015); Zhang, Bengio, Hardt, Recht and Vinyals on [arXiv 1611.03530](https://arxiv.org/abs/1611.03530) (v2; ICLR 2017); Belkin, Hsu, Ma and Mandal on [arXiv 1812.11118](https://arxiv.org/abs/1812.11118) (v2, 10 September 2019).

| # | Claim | Source |
|---|-------|--------|
| B1 | The stochastic gradient method was proposed by Robbins and Monro (*The Annals of Mathematical Statistics* 22(3):400–407, 1951), first not as a gradient method but as a Markov chain; logistic regression gives convex optimization problems, deep neural networks highly nonlinear and nonconvex ones | Quote: §1, Inset 3.1 and reference [130] (in `gradient-descent`) |
| A1 | Adam keeps exponentially decaying estimates of the first moment of the gradient and of its elementwise square, corrects both for their initialization at zero, and updates by `α m / (sqrt(v) + ε)`; good default settings for the tested problems are α = 0.001, β1 = 0.9, β2 = 0.999 and ε = 10⁻⁸; the magnitudes of the updates are invariant to rescaling of the gradient | Quote: abstract, §1 and Algorithm 1 (in `gradient-descent`) |
| Z1 | State-of-the-art convolutional networks for image classification trained with stochastic gradient methods easily fit a random labeling of the training data; this is qualitatively unaffected by explicit regularization; traditional approaches fail to explain why large networks generalize | Quote: abstract (in `overfitting-and-regularization`) |
| BE1 | A "double descent" curve subsumes the textbook U-shaped bias-variance curve: increasing capacity beyond the point of interpolation improves performance | Quote: abstract (in `overfitting-and-regularization`) |

## Classifier metrics and calibration

Fawcett, *Pattern Recognition Letters* 27(8):861–874, 2006, DOI 10.1016/j.patrec.2005.10.010, read from a copy of the published article on a university course page; Davis and Goadrich, ICML 2006, pages 233–240, DOI 10.1145/1143844.1143874, read from the copy on the University of Wisconsin's machine learning server; Saito and Rehmsmeier, *PLOS ONE* 10(3):e0118432, 2015; Naeini, Cooper and Hauskrecht, AAAI 2015, pages 2901–2907, read on PubMed Central (PMC4410090); Guo, Pleiss, Sun and Weinberger on [arXiv 1706.04599](https://arxiv.org/abs/1706.04599) (v2, 3 August 2017); Niculescu-Mizil and Caruana, ICML 2005, from the authors' [PDF](https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf); Gneiting and Raftery, *JASA* 102(477):359–378, 2007, DOI 10.1198/016214506000001437, read from the copy on the second author's university page. The DOIs' metadata was checked on Crossref. Used in `classifier-metrics`, and Fawcett and Saito and Rehmsmeier also in `evaluation-pitfalls`.

| # | Claim | Source |
|---|-------|--------|
| F1 | The true positive rate is also called hit rate and recall, the false positive rate false alarm rate; sensitivity equals recall, specificity is `TN / (FP + TN)`, which is `1 - fp rate`, and positive predictive value is precision; a discrete classifier is a single point in ROC space; `(0, 0)` never issues a positive classification, `(1, 1)` always does, `(0, 1)` is perfect; ROC graphs have long been used in signal detection theory | Quote: §1 to §3 and Fig. 1 |
| F2 | ROC curves are insensitive to changes in class distribution, since the true and false positive rates are each a ratio within one column; accuracy, precision, lift and F score use both columns and change with the class distribution even when the classifier does not; class skews of 10 and 100 are very common in real domains, and up to 10⁶ have been observed | Quote: §4.2 |
| F3 | The AUC is always between 0 and 1, and random guessing gives 0.5; it equals the probability that the classifier ranks a randomly chosen positive above a randomly chosen negative, equivalent to the Wilcoxon test of ranks (Hanley and McNeil, 1982); Gini + 1 = 2 · AUC (Hand and Till); a high-AUC classifier can perform worse than a low-AUC one in a specific region of ROC space | Quote: §7 |
| DG1 | A curve dominates in ROC space if and only if it dominates in precision-recall space; it is incorrect to linearly interpolate between points in PR space; algorithms that optimize the area under the ROC curve are not guaranteed to optimize the area under the PR curve; PR curves give a more informative picture on highly skewed datasets | Quote: abstract |
| SR1 | The precision-recall plot is more informative than the ROC plot on imbalanced datasets; its baseline is `y = P / (P + N)`, 0.5 for balanced classes and 0.09 for a P:N ratio of 1:10, and the AUC of the PR curve of a random classifier is `P / (P + N)` | Quote: abstract and the section on PRC plots |
| N1 | A set of binary predictions is well calibrated if outcomes predicted with probability p occur about a p fraction of the time; ECE is the sum over bins of the fraction of instances in the bin times the absolute difference between the bin's true fraction of positives and its mean predicted probability; MCE is the maximum of those differences; the experiments use K = 10 bins | Quote: §*Calibration measures*, read with WebFetch on PubMed Central |
| GU1 | Modern neural networks, unlike those from a decade ago, are poorly calibrated; reliability diagrams plot expected accuracy as a function of confidence, the identity function for a perfectly calibrated model; ECE groups predictions into M equally spaced bins and takes the size-weighted average of the gap between accuracy and confidence; MCE takes the worst case; Platt scaling uses a classifier's outputs as features for a logistic regression trained on the validation set; temperature scaling, a single-parameter variant of Platt scaling, is surprisingly effective; isotonic regression (Zadrozny and Elkan, 2002) learns a piecewise constant function | Quote: abstract, §2 and §4.1 |
| NM1 | Maximum margin methods push probability mass away from 0 and 1 in a sigmoid-shaped distortion, while methods with unrealistic independence assumptions push it toward 0 and 1, and others predict well-calibrated probabilities; Platt scaling is most effective when the distortion is sigmoid-shaped; isotonic regression corrects any monotonic distortion but is more prone to overfitting when data is scarce | Quote: abstract and §1 |
| GR1 | A scoring rule is proper if a forecaster maximizes the expected score by issuing the forecast it believes, and strictly proper if that maximum is unique; the quadratic or Brier score, `S(p, i) = -sum over j of (δij - pj)²`, was proposed by Brier (1950); the logarithmic score is `log pi`; the scores of Examples 1 to 3, quadratic, spherical and logarithmic, are strictly proper; the logarithmic score has been criticized for its unboundedness | Quote: abstract and §3, Examples 1 and 3 |

## Python

The documentation at `docs.python.org/3` (3.15.2); the examples run on CPython 3.13.12.

| # | Claim | Source |
|---|-------|--------|
| PY1 | `statistics.linear_regression` returns the slope and intercept of simple linear regression estimated by ordinary least squares; both inputs must have the same length, at least two, and x cannot be constant, or `StatisticsError` is raised; added in 3.10; `proportional` added in 3.11, fitting a line through the origin | Quote: [statistics](https://docs.python.org/3/library/statistics.html#statistics.linear_regression); run: `fit_a_line.py` (in `linear-and-logistic-regression`) |
| PY2 | Reusing a seed reproduces a sequence; most of the module's algorithms and seeding functions may change across versions, but a backward compatible seeder will be offered and `random()` will continue to produce the same sequence for the same seed | Quote: [random, *Notes on Reproducibility*](https://docs.python.org/3/library/random.html#notes-on-reproducibility) (in `data-splits-and-leakage`, and the reason every example draws only from `random()`) |
| PY3 | As a CPython implementation detail, the `math` module raises `ValueError` for invalid operations such as `log(0.0)` and `OverflowError` for results that overflow, such as `exp(1000.0)`; `math.exp(709)` returns a number and `math.exp(710)` raises `OverflowError: math range error` | Quote: [math](https://docs.python.org/3/library/math.html); run: a one-off program (in `linear-and-logistic-regression`) |

## The examples and the arithmetic

| # | Claim | Source |
|---|-------|--------|
| E1 | Split by row the customer-recognizing model scores 0.88; split by customer 0.70, the same as always saying "kept" | Run: `split_by_customer.py` |
| E2 | Least squares gives slope 2.3611 and intercept 13.5556 by hand and from `statistics.linear_regression`, 37.2 minutes at 10 km and an MSE of 0.594; moving the slope by 0.2 either way adds 3.7, which is 0.2² times the mean squared distance 92.5, and moving the intercept by 1 adds 1, since the residuals of a least squares fit with an intercept average to zero | Run: `fit_a_line.py`; arithmetic: (4 + 16 + 25 + 49 + 81 + 144 + 196 + 225) / 8 = 92.5 |
| E3 | The sigmoid of -4, -2, 0, 2, 4 and the log odds that undo it; `sigmoid(-z) = 1 - sigmoid(z)`; the log loss and squared error at seven probabilities, 4.605 against 0.980 at 0.01; `ln 2 = 0.693`; `e^z / (1 + e^z)` equals the sigmoid | Run: `log_loss.py`; arithmetic |
| E4 | The one-weight loss has curvature 15, so rates below 2/15 = 0.1333 converge, since each step multiplies the distance to the best weight by `1 - rate * curvature`; the best weight is 1.99 with loss 0.0243; the table of four rates, the last diverging to a loss of 1,344.26 | Run: `learning_rates.py`; arithmetic: the factor's size must be below 1 |
| E5 | With the area in square metres the curvatures are 1.334 × 10⁴ and 0.09914, a condition number of 1.346 × 10⁵, and after 10,000 steps the loss is still 27.28 above its lowest; standardized, both are 2 and one step at rate 0.5 reaches the bottom | Run: `scaling.py` |
| E6 | The k-nearest-neighbour table, test error lowest at k = 3 (0.871), about twice the noise at k = 1 (1.484), and the second worst model being the one the training error prefers; the noise's MSE is 3² / 12 = 0.75 | Run: `neighbours.py`; arithmetic: the variance of a uniform spread over a width of 3 |
| E7 | Least squares gives weights 10.20 and -8.25, adding up to about 2, with a test error 4.4 times the training error; a disagreement of one unit between the measurements moves the prediction by (10.20 + 8.25) / 2, about 9; with `n * strength` on the diagonal, the penalized mean squared error of the guide, strengths 0.01 and 0.1 lower the test error by about a quarter and 1 raises both errors | Run: `ridge_shrinkage.py`; arithmetic: one measurement half a unit above the size and the other half a unit below |
| E8 | Positives held out per fold: [0, 0, 6] as stored, [4, 1, 1] after a shuffle, [2, 2, 2] stratified | Run: `stratified_folds.py` |
| E9 | Of 50 coin-flip models on 40 validation examples, the worst scores 0.325, the median 0.512, the best 0.675, and the best scores 0.509 on fresh data; one answer of 40 moves an accuracy by 2.5 points | Run: `winners_curse.py`; arithmetic |
| E10 | The confusion matrix and rates at five thresholds; the best F1, 0.714, at 0.35; 28 of the 36 spam and good-email pairs in order, an AUC of 0.778 | Run: `thresholds.py`, and a one-off program counting the pairs |
| E11 | The honest and base-rate forecasters have a calibration error of 0, Brier scores 0.190 and 0.250 and log losses 0.565 and 0.693; the overconfident one 0.127, 0.214 and 0.850 | Run: `calibration.py` |
| E12 | For the two-class case, the quadratic score of GR1 is `-2 (p - y)²`, twice the one-number Brier form the guide uses | Arithmetic: `(1 - p)² + (0 - (1 - p))²` for an outcome of 1 |
| E13 | At base rates of 50%, 10%, 1% and 0.1%, the classifier's precision is 0.947, 0.667, 0.154 and 0.018, its accuracy 0.925 to 0.950; 5,085 flags find 90 positives at 0.1% | Run: `base_rates.py` |
| E14 | A 2.7-point lead built on 22 against 14 disagreements; a 95% paired bootstrap interval from -0.013 to +0.067; A at least as good in 10.4% of 2,000 resamples; each model's own interval is 0.087 and 0.083 wide, about the width of the difference's (0.080); 600,000 draws in all | Run: `paired_bootstrap.py`, and a one-off program for the single-model intervals; arithmetic: 2,000 × 300 |
| E15 | Half a point of accuracy on 1,000 cases is five answers; with a constant factor per step, the steps needed grow with the logarithm of the precision wanted | Arithmetic |
| E16 | The complexity tables: operation counts of the algorithms as written, such as O(n d²) to form `X^T X` and O(d³) to solve it, O(n log n) to sort scores, O(B n) for `B` bootstrap resamples of `n` cases | Arithmetic |
| E17 | `\|w\|` has slope -1 left of 0 and +1 right of it, and none at 0, so plain gradient descent does not apply to an L1 penalty as it stands | Arithmetic |

## Citations and names

The guides name no company, product or vendor. Papers and books are cited by their authors, and the affiliations printed in them are not repeated. Where a paper names the systems or datasets it studied, the guides leave them out: Recht and others' two benchmarks are "two long-used image benchmarks", and appear only in the paper's own title in the further reading; Kohavi's two learning algorithms and Niculescu-Mizil and Caruana's model families are described, not named. Python's standard library is the language of the examples, cited from its official documentation; no third-party library is named or used.

## Not read in the original

- Brier (1950): not read; cited through Gneiting and Raftery, who attribute the quadratic score to Brier. The guide defines the Brier score as the calibration problem does.
- Hanley and McNeil (1982): not read; the AUC's equivalence with the Wilcoxon test is cited through Fawcett.
- Hoerl and Kennard (1970): not read; cited through ESL.
- Tibshirani (1996): not read; cited through ESL.
- Robbins and Monro (1951): not read; cited through Bottou, Curtis and Nocedal.
- Efron (1979): not read; cited through ESL.
- Polyak (1964): not read; cited through *Deep Learning*.
- Platt (1999): not read; cited through Guo and others and through Niculescu-Mizil and Caruana.
- Zadrozny and Elkan (2002): not read; cited through Guo and others and through Niculescu-Mizil and Caruana.
- Kaufman and others (2012): not read; not cited.
- Dietterich (1998): not read, since the only copy found has an unreadable text layer; the guides name no significance test, such as McNemar's, and use the bootstrap, cited through ESL.
- Bergmeir, Hyndman and Koo (2018), and a forecasting textbook's page on time-series cross-validation: not read; forward-in-time validation is described from Kapoor and Narayanan's rule on temporal leakage, with no citation for the procedure itself.
- Davis and Goadrich, and Gneiting and Raftery: their DOI links resolve to publishers that refuse automated requests (HTTP 403); their metadata is checked on Crossref, and the papers are read from the copies named above.
- The paradox of an average that reverses within every group is described, not named.
- No trap repeats hints 3 and 5 of `gradient-descent-models`, updating the weights one at a time and reusing a model across folds, although its statement states both rules.

## Practice links

The guides link three problems, all on `main`. Each problem's `meta.yaml` lists its guides after `related:`:

| Problem | `guides:` |
|---------|-----------|
| 0258 `calibration-metrics` | `[classifier-metrics, evaluation-pitfalls]` |
| 0352 `classification-metrics` | `[classifier-metrics, evaluation-pitfalls]` |
| 0353 `gradient-descent-models` | `[data-splits-and-leakage, linear-and-logistic-regression, gradient-descent, overfitting-and-regularization, cross-validation, evaluation-pitfalls]` |

The path takes `gradient-descent-models` three times: to level 2 after the guide on gradient descent, to level 3 after cross-validation, and through all four levels after the capstone, since level 4 (early stopping and leakage) draws on every guide before it.

## Where a guide comes close to a linked problem

Each guide teaches its idea with examples of its own, but some ideas are the problem's subject. These are the places the review should weigh against the rule that a guide never gives away a linked problem's solution:

| Guide | Close to | What the guide shows | Kept back |
|-------|----------|----------------------|-----------|
| `data-splits-and-leakage` | `gradient-descent-models` level 4 | The leakage taxonomy and ESL's 3%-against-50% result in prose; a split by customer on other data | No scaler, correlation or feature choice in code |
| `linear-and-logistic-regression` | `gradient-descent-models` levels 1 and 2 | The MSE, the sigmoid and the log loss as the statement defines them; a closed-form one-feature fit and a loss table on other data; clipping named as practice, without the problem's ε | No gradient code, training rows or rounding; the unclipped-p gradient and the factor-2 pitfall are not discussed |
| `gradient-descent` | `gradient-descent-models` levels 1 and 4 | The MSE gradient step for one weight and for a weight and a bias, on other data; the divergence threshold `2 / curvature`, which the problem's explanation derives in its correctness section; standardization with `statistics.pstdev` on data with no split, with the prose saying the mean and spread come from the training set when there is one | No logistic gradient, rows, rounding or early stopping loop; the "slopes before any weight moved" rule appears only as the statement words it, and no trap repeats hint 3 |
| `overfitting-and-regularization` | `gradient-descent-models` levels 3 and 4 | The L2 penalty with the bias left out (stated in the problem), ridge in closed form for two features, k-nearest-neighbour capacity, early stopping in prose | No ridge by gradient descent, no folds, no patience loop or best-weights bookkeeping (hint 6) |
| `cross-validation` | `gradient-descent-models` level 3, and level 4's selection check | k-fold in prose; stratified folds dealt round the folds, unlike the statement's consecutive blocks; choosing the best of 50 coin-flip models, the same lesson as level 4's example 3, with no features, correlations or training | No code for the statement's fold bounds; no trap repeats the fresh model per fold of hint 5; no tie rule for choosing a strength |
| `classifier-metrics` | `classification-metrics` | The binary confusion matrix and its rates at five thresholds, computed by plain division with no empty denominator; F1 as a harmonic mean; the AUC as the pair probability the statement defines, counted in prose; macro and micro averages in one sentence each, as the statement defines them; the complexity table gives the AUC by pairs, O(P N), and a sort only for drawing curves | No zero-denominator helper (hint 2), no rank-sum AUC (hint 4), no ties, per-class rows, averages in code or rounding. Follow-up 3 (precision-recall against ROC under skew) and follow-up 1 (on which data to choose a threshold) are answered in general |
| `classifier-metrics` | `calibration-metrics` | A calibration error as the size-weighted gap, with one group per stated probability; the Brier score; the base-rate forecaster that is calibrated and useless, which the problem's explanation also notes | No bins, bin index or `p = 1.0` cap (hint 3), no cancellation of the bin size (hint 1), no slices in code (hint 2) |
| `evaluation-pitfalls` | `classification-metrics` follow-up 2, `calibration-metrics` follow-up 3, `gradient-descent-models` level 4 | A paired bootstrap of an accuracy difference; the advice to report a small group's size and interval; the practice line describes level 4 as its statement does | No per-class interval method; nothing of level 4's code |
| `gradient-descent` | `gradient-descent-models` follow-ups 1 and 2 | Minibatch and stochastic steps, why their noise calls for a decaying rate, and when a closed form is cheaper than gradient descent (`d³` for `d` features) | Nothing of the follow-ups' specific questions about what a test would fix |
| `cross-validation`, `data-splits-and-leakage` | `gradient-descent-models` follow-ups 3, 4 and 5 | The winner's curse and nested cross-validation (3); folds on data sorted by label, and splits by time (4); fitting every learned step inside each fold, on the training part only (5) | Nothing of the problem's own `chooseStrength`, fold bounds or scaler |
| `classifier-metrics` | `classification-metrics` pitfall `h8` | The trap of computing the AUC from yes-or-no answers instead of the scores | No test case, and no AUC code |

## Independent accuracy review (2026-11-13)

The review checks every claim of the seven guides against the source this page gives for it, runs every example and compares what it prints with the guide, and reads the guides against the linked problems' statements, hints and solutions. It finds no wrong citation and no spoiler; all 13 examples and the arithmetic match, and the second-hand citations are attributed to the sources that make them. These are its findings and what changes.

| # | Finding | Change |
|---|---------|--------|
| 1, 17 | The README and ADR 0025 path lists change in the next release, and the integrator updates the list and the counts when this branch merges | This branch leaves both files as they are on `main` |
| 2 | `classifier-metrics` said the overconfident forecaster gives "the same answers" at any threshold | Every split one can make with a threshold the other can make with some threshold, so the AUC is the same |
| 3 | `classifier-metrics` named only the rainy days the overconfident forecaster called at 1% | It also names the two dry days it called at 99% |
| 4 | `overfitting-and-regularization` defines the penalty on the mean squared error, while its example added the strength itself to the diagonal of the summed equations | The example adds `n * strength`, keeping the guide's definition and the scale of `gradient-descent-models`; the strengths are 0, 0.01, 0.1 and 1, and the table is the same (E7) |
| 5 | "Ten times as much as it should" had no basis | The noise between the measurements moves the price by about 9 per unit of disagreement, when it should not move it at all (E7) |
| 6 | `classifier-metrics`: an AUC of 0.5 does not mean the scores say nothing | 0.5 is what scores that say nothing get, as a coin flip would |
| 7 | `classifier-metrics`: a reliability diagram is not the expected calibration error's comparison itself | Guo and others draw a version of it for the predicted class (GU1) |
| 8 | `overfitting-and-regularization` did not name the trade-off it introduced | The **bias-variance trade-off** (H5) |
| 9 | The statistical bias could be confused with a linear model's bias | The guide says they are the same word for different things |
| 10 | `cross-validation`: recall is not the only number a fold with no positive cannot measure | How many positives the model finds cannot be measured |
| 11 | `linear-and-logistic-regression` wrote the normal equations with `b`, the guide's name for the bias alone | `w` holds the bias and the weights, in `X^T (y - X w) = 0` and `w = (X^T X)^(-1) X^T y` (H1) |
| 12 | `linear-and-logistic-regression` used "negative log-likelihood" and "gradient methods" before defining them | A plain gloss of the likelihood, and gradient descent named as the next guide's method |
| 13 | `gradient-descent` gave "most losses with a penalty that has no closed form" without an example | L2 on a large model, and an L1 penalty, which needs a variant since `\|w\|` has no slope at 0 (E17) |
| 14 | `evaluation-pitfalls` counted the bootstrap's sort twice | O(B n + B log B) time and O(B) space for the differences |
| 15 | `data-splits-and-leakage` said "correlate" in an intro guide, and that the notes "quote" a case they paraphrase | The features that move most closely with the label; the notes describe the case |
| 16 | `cross-validation`: "naive standard error" was jargon | An error bar computed as if the folds were independent is too small (G1) |
| 18 | History wording on this page | The section on second-hand citations states what was not read and where each claim is cited from |
| 19 | The table of places close to a problem missed three | Rows for `gradient-descent-models` follow-ups 1 to 5 and for `classification-metrics` pitfall `h8` |
