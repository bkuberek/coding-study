# Classification Metrics

## Statement

A model reads support tickets and says which kind each one is: a billing question, a bug report, an account problem. Before anyone trusts it, it is run on tickets whose answer is already known, and its answers are compared with the truth. Write `classificationMetrics`, which does that comparison and reports how good the model is, class by class and overall.

**Labels, scores and predictions.** The kinds are the **classes**, numbered `0` to `k - 1`. Each ticket has a **label**: the class it really belongs to, decided by a person. For each class, the model gives the ticket a **score** from 0 to 1: how strongly it believes the ticket is of that class. A score is not yet an answer. To turn it into a yes or a no you pick a **threshold**: the model **predicts** "this ticket is of class `c`" when its score for `c` is at least the threshold, so a score equal to the threshold counts as a yes. Each class is asked on its own, so a ticket can get a yes from several classes, or from none.

**One class at a time.** For class `c`, every ticket is a **positive** when its label is `c` and a **negative** otherwise, and the prediction for `c` is a yes or a no. That gives four outcomes, counted over all tickets:

- **TP** (true positives): positive, and the model said yes.
- **FP** (false positives): negative, but the model said yes, a false alarm.
- **FN** (false negatives): positive, but the model said no, a miss.
- **TN** (true negatives): negative, and the model said no.

These four counts are the class's **confusion matrix**, and every rate below is built from them:

- **Accuracy** = `(TP + TN) / n`, where `n` is the number of tickets: the share of answers that were right.
- **Precision** = `TP / (TP + FP)`: of the tickets the model called `c`, the share that were `c`.
- **Recall** = `TP / (TP + FN)`: of the tickets that were `c`, the share the model found.
- **F1** = `2 * precision * recall / (precision + recall)`, the harmonic mean of the two, which is high only when both are. In counts it is `2 TP / (2 TP + FP + FN)`.

A rate whose denominator is 0 is **0**: precision when the model never says yes, recall when the class has no positives, and F1 when precision and recall are both 0.

**ROC-AUC.** Every rate above depends on the threshold, which is a choice. The **area under the ROC curve** (AUC) measures the scores themselves, at every threshold at once: take every pair of one positive and one negative ticket of class `c`, and count the pairs in which the positive has the higher score for `c`, a pair with equal scores counting one half. The AUC is that count divided by the number of pairs, `positives * negatives`. It is the chance that a random positive outscores a random negative: 1 when the scores put every positive first, 0.5 when they say nothing, 0 when they are upside down. A class with no positive or no negative ticket has no pairs, and its AUC is **-1**, meaning "not defined".

**Averages over the classes.**

- **Macro** averages give each class the same weight: the plain mean of the classes' precision, of their recall, and of their F1, over all `k` classes. The macro AUC is the mean over the classes whose AUC is defined.
- **Micro** averages give each answer the same weight: add up TP, FP and FN over all classes first, then compute precision, recall and F1 once from the totals.

**Rounding.** Every rate is rounded to 6 decimal places, a value exactly halfway being rounded up (`0.0000005` becomes `0.000001`). Averages are computed from the unrounded rates, and only the result is rounded. The tests never put a rate exactly halfway or near it, so any correct way of rounding to 6 places gives the same answer. Counts and the `-1` of an undefined AUC are whole numbers and need no rounding.

## Input

- `labels`: `labels[i]` is the true class of ticket `i`.
- `scores`: `scores[i][c]` is the model's score for ticket `i` and class `c`. Every row has `k` entries, so the number of classes is the length of a row. The scores of a row need not add up to 1.
- `threshold`: the model says yes for class `c` when `scores[i][c] >= threshold`.

## Output

`k + 2` rows:

- Rows `0` to `k - 1`, one per class: `[TP, FP, FN, TN, accuracy, precision, recall, F1, AUC]`.
- Row `k`, the macro averages: `[precision, recall, F1, AUC]`.
- Row `k + 1`, the micro averages: `[precision, recall, F1]`.

Numbers are compared with a tolerance of `10^-9`, which is far smaller than the last rounded digit.

## Examples

### Example 1

<!-- case: ex1 -->

Six emails, class 1 is spam and class 0 is not. Work through class 1 by hand. Its scores are `0.9, 0.6, 0.3` for the three spam emails and `0.2, 0.65, 0.1` for the others. At the threshold 0.5 the model says yes to `0.9`, `0.6` and `0.65`: two spams caught (TP = 2), one good email flagged (FP = 1), one spam missed at `0.3` (FN = 1) and two good emails left alone (TN = 2). Accuracy is `4 / 6`, precision `2 / 3`, recall `2 / 3`, and F1 `2 * 2 / (2 * 2 + 1 + 1) = 2 / 3`, each rounded to `0.666667`. For the AUC, pair each spam with each good email, 9 pairs: `0.9` beats all three, `0.6` beats `0.2` and `0.1`, and `0.3` beats `0.2` and `0.1`, so 7 of 9 pairs are in the right order, `0.777778`. Class 0's scores are the mirror image, so its row is the same, and both averages repeat it.

### Example 2

<!-- case: ex2 -->

One transaction in ten is fraud (class 1). The model gives the fraud a higher fraud score (`0.4`) than any honest transaction, but never reaches the threshold of 0.5, so it never says "fraud". Class 1's accuracy is still `0.9`, because nine of the ten answers ("not fraud") are right, and yet the model found nothing: recall 0, and precision 0 by the rule for an empty denominator. This is why accuracy misleads when one class is rare: always answering "no" scores as well as the share of negatives. The macro F1, `0.473684`, shows the problem, since the fraud class counts as much as the common one. The AUC of 1 shows that the scores rank perfectly: here the threshold is what fails, not the model.

### Example 3

<!-- case: ex3 -->

Three classes, and the threshold counts a score of exactly 0.5 as a yes. The third ticket (class 0) gets a yes from class 0 and from class 1, and the sixth (class 1) gets a yes only from class 0, a false positive for class 0 and a miss for class 1. In class 0's AUC, the third ticket and the sixth tie at `0.5` and count one half: `14.5 / 16 = 0.90625`. The macro precision is the mean of `0.75`, `1 / 3` and `0.5`, while the micro precision pools the counts, `5 / (5 + 4) = 0.555556`, so the two averages tell different stories.

## Constraints

- `1 <= labels.length == scores.length <= 1000`.
- `2 <= k <= 10`, and every row of `scores` has `k` entries.
- `0 <= labels[i] < k`, and `labels` holds at least two different classes.
- `0 <= scores[i][c] <= 1` and `0 <= threshold <= 1`.

## Follow-ups

- The threshold here is the same for every class. How would you choose one per class, and on which data, so that the choice does not flatter the results?
- A rare class has few positives, so one more or one fewer catch moves its recall a lot. How would you show the uncertainty of a per-class number?
- Precision and recall pull against each other as the threshold moves. Draw recall against precision for every threshold: what does it show that the ROC curve hides when negatives vastly outnumber positives?
- A weighted average gives each class a weight equal to its number of positives. When is it closer to the macro average, and when to the micro one?

## Hints

### Hint 1

Start with one class, and forget the others. For every ticket you know two things: is it really of this class (yes or no), and did the model say it is (yes or no). Four combinations are possible. Count how many tickets fall into each, and check your counts on Example 1 before going further.

### Hint 2

Every rate is one count divided by a sum of counts. Write one small helper that divides and returns 0 when the denominator is 0, and use it for precision, recall and F1.

### Hint 3

For the averages, keep the unrounded rates of every class and the counts of every class. Macro averages the rates; micro adds the counts first and divides once. Round only at the very end.

### Hint 4

For the AUC, comparing every positive with every negative is correct and fine at this size. To do it faster, sort the class's scores once and give each score its rank, tied scores sharing the average of their ranks. The ranks of the positives add up to `wins + P (P + 1) / 2`, where a win is a pair the positive takes and a tie is half a win, so `AUC = (sum of the positives' ranks - P (P + 1) / 2) / (P * N)`, with `P` positives and `N` negatives.
