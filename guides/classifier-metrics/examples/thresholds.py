"""One set of scores, five thresholds: the confusion matrix and its rates at each.

Twelve emails scored by a spam filter, six of them spam (the positives). Moving the threshold
trades false alarms against misses.
"""

spam = [0.95, 0.85, 0.70, 0.62, 0.40, 0.30]
not_spam = [0.80, 0.55, 0.45, 0.20, 0.15, 0.05]

print("threshold  TP FP FN TN  precision  recall     F1  false positive rate")
for threshold in [0.90, 0.75, 0.50, 0.35, 0.10]:
    tp = sum(score >= threshold for score in spam)
    fp = sum(score >= threshold for score in not_spam)
    fn, tn = len(spam) - tp, len(not_spam) - fp
    precision, recall = tp / (tp + fp), tp / (tp + fn)
    f1 = 2 * precision * recall / (precision + recall)
    counts = f"{tp:2} {fp:2} {fn:2} {tn:2}"
    rates = f"{precision:9.3f}  {recall:6.3f}  {f1:.3f}  {fp / (fp + tn):19.3f}"
    print(f"{threshold:9.2f}  {counts}  {rates}")
