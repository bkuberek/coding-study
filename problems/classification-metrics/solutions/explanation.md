# Classification Metrics: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| counts-and-rank-sum | optimal | O(k n log n) | O(n) | default answer |

`n` is the number of tickets and `k` the number of classes.

## Approach: counts-and-rank-sum (Count the four outcomes per class and rank the scores once for the AUC)

### Intuition

Every number in the report answers one of two questions. The first: at this threshold, how do the model's yes and no answers line up with the truth? The four counts of the confusion matrix hold all of that, so the rates are just ways of dividing them. Accuracy divides the right answers by all answers, which is why it is fooled by a rare class: when 90% of tickets are negatives, "always no" is 90% accurate. Precision and recall look only at the positives, from the two sides: of what the model flagged, how much was right, and of what was there, how much it found. F1 is their harmonic mean, which stays low when either one is low, unlike the plain mean.

The second question ignores the threshold: do the scores put the positives above the negatives? The AUC counts the pairs that are in the right order. It is the same as the area under the ROC curve, which plots recall against the false positive rate as the threshold sweeps from 1 down to 0: a pair of one positive and one negative becomes "in order" exactly when the curve climbs before it moves right. A tie is a pair that no threshold can separate, so it gets half credit, which is the diagonal step the ROC curve takes through a run of equal scores.

Example 2 shows why both questions matter: AUC 1 (the ranking is perfect), and recall 0 (the threshold is too high). The fix there is a better threshold, not a better model.

### Algorithm

1. For each class `c`, mark each ticket positive when `labels[i] == c`, and take the column `scores[i][c]`.
2. Count TP, FP and FN by comparing each mark with `score >= threshold`; TN is `n - TP - FP - FN`.
3. Compute accuracy, precision, recall and F1 from the counts, with 0 for an empty denominator. F1 uses the count form `2 TP / (2 TP + FP + FN)`.
4. For the AUC, return -1 when the class has no positive or no negative. Otherwise sort the tickets by score, walk the runs of equal scores, and give every ticket in a run the average rank of the run. Add up the ranks of the positives as `R`; the AUC is `(R - P (P + 1) / 2) / (P * N)`. The code keeps twice the ranks, so that every average rank is a whole number.
5. Round the per-class rates. The macro row is the mean of the unrounded precision, recall and F1 over all classes, and of the AUC over the defined ones. The micro row adds TP, FP and FN over the classes and applies step 3 to the totals.

### Correctness

The four outcomes are exclusive and cover every ticket, so the counts add up to `n` and TN can be derived. The count form of F1 equals `2PR / (P + R)` whenever `TP > 0`: multiply the top and bottom by `(TP + FP)(TP + FN) / TP`. When `TP = 0`, precision and recall are both 0, by division or by the rule, so the harmonic mean is 0 by the rule, and the count form gives `0 / (FP + FN)`, or 0 by the rule when that is also 0. The two forms always agree.

For the AUC, sort all `n` scores and give tied scores their average rank. Take a positive with rank `r`. The tickets strictly below it are the ones before its run, and each tie in its run adds one half to its average rank beyond those (`(start + end + 2) / 2` is the number of tickets before the run, plus one, plus half of the others in the run). So the rank of a positive is `1 + (tickets it beats) + (tickets it ties) / 2`, counting itself once. Adding over the positives, the pairs of two positives contribute exactly `P (P - 1) / 2` wins and ties together, and the `1` per positive adds `P`, which together make `P (P + 1) / 2`. What remains is the sum, over positive and negative pairs, of 1 for a win and one half for a tie, the definition. This is the Mann-Whitney U statistic, and dividing it by `P * N` gives the AUC.

### Complexity

- Time: O(k n log n) — each class sorts its `n` scores once; the counts and the rank walk are linear.
- Space: O(n) — the marks, the score column and the sorted order of one class at a time, plus O(k) rates.

### Trade-offs

Comparing every positive with every negative is the definition and easy to check, but it costs `P * N` comparisons per class, up to `n^2 / 4`. At the constraints of this problem that is a quarter of a million per class, so it is fine here, and the rank sum is what scales to a million examples.

A one-vs-rest report treats every class as its own yes-or-no question, with one shared threshold. A model that must give exactly one class per ticket takes the class with the highest score instead, and then the report is one `k`-by-`k` confusion matrix of true class against predicted class. Each class's TP, FP and FN are still read off it (its diagonal cell, the rest of its column and the rest of its row), and the micro precision, recall and F1 all equal the accuracy, since every wrong answer is one false positive and one false negative.

Macro and micro answer different questions. Micro is dominated by the large classes, so it says how good the typical answer is. Macro lets a small class pull the average down, so it says whether some class is being neglected (`h10`). A weighted average, by the number of positives of each class, sits between them.

### Pitfalls and edge cases

- **`>` for `>=`.** A score equal to the threshold is a yes (`ex3`, `h1`).
- **Ties in the AUC.** A tie counts one half, not 0 or 1; when every score of a class is the same, the AUC is exactly 0.5 (`h2`, `h12`). Ranking with plain positions instead of average ranks makes the answer depend on how the sort orders equal scores (`h12`).
- **The AUC from the answers instead of the scores.** Ranking the yes and no answers treats the model as if it had only two scores, and loses everything the ranking knows (`h8`: no answer is yes, yet the AUC is 1).
- **Empty denominators.** Precision with no yes, recall with no positive, and F1 with neither must be 0, not `NaN`, not a crash, and not 1 (`ex2`, `h3`, `h4`, `h8`).
- **F1 as the plain mean.** `(P + R) / 2` rewards a model that is good at one and useless at the other (`h1`).
- **Macro F1 from the macro precision and recall.** The macro F1 is the mean of the per-class F1 values; the harmonic mean of the macro precision and the macro recall is a different number (`h1`, `h10`).
- **Micro as a second macro.** Micro adds the counts before dividing; averaging the per-class rates is macro (`h10`).
- **An undefined AUC in the mean.** A class without positives has no AUC; it is reported as -1 and left out of the macro AUC, not counted as 0, -1 or 0.5 (`h3`, `h4`). Its precision, recall and F1 do count in the macro mean, as 0, which is the rule this report chose; some libraries let you leave such classes out instead.
- **Rounding.** Round to the nearest 6-decimal value, not down: `4 / 7` is `0.571429` (`h1`, `h11`). Rounding the per-class rates before averaging can move the last digit of a mean, so the averages use the unrounded rates.
- **Accuracy alone.** On a rare class, "always no" is accurate and useless (`ex2`).

### Language notes

- Python: `sum(is_positive)` counts the `True` values, since a `bool` is an `int`. Sorting indexes with `key=lambda index: class_scores[index]` keeps the scores and the marks in step.
- TypeScript: sorting the indexes needs the comparator `(a, b) => classScores[a] - classScores[b]`, since the default `sort` compares its elements as text, which would put index 10 before index 2 and ignore the scores. `Math.floor(value * 1_000_000 + 0.5) / 1_000_000` is the same rounding, done with the same double operations, as in Python, so both references return the same doubles. Python's built-in `round(value, 6)` rounds a value exactly halfway to the even digit instead, which the tests never tell apart.

## Further reading

- T. Fawcett, "An introduction to ROC analysis", Pattern Recognition Letters 27(8):861-874, 2006, doi:10.1016/j.patrec.2005.10.010: the confusion matrix and the rates built from it (figure 1), why ROC curves stay the same when the class balance changes while accuracy, precision and F-score do not (section 4.2), why a run of equally scored instances should be drawn as a diagonal, the expected performance (section 5), and the AUC as the probability that a random positive is ranked above a random negative, equivalent to the Wilcoxon test of ranks (section 7).
- J. A. Hanley and B. J. McNeil, "The meaning and use of the area under a receiver operating characteristic (ROC) curve", Radiology 143(1):29-36, 1982, doi:10.1148/radiology.143.1.7063747: the area under the curve as the probability that a randomly chosen diseased subject is rated as more likely diseased than a randomly chosen healthy one, and its equality with the Wilcoxon statistic.
- [scikit-learn, `precision_recall_fscore_support`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.precision_recall_fscore_support.html): precision and recall from counts, the `micro`, `macro` and `weighted` averages, and the `zero_division` rule, whose default, `"warn"`, acts like 0 for an undefined precision, recall or F-score and also raises a warning.
- [scikit-learn, `roc_auc_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html) and [`roc_curve`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_curve.html): one-vs-rest AUC for several classes, its macro average, and rates computed for the predictions with `score >= threshold`.
