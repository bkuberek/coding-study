"""The same classifier at four base rates: its recall and false positive rate stay put, its
precision and accuracy do not.

The classifier finds 90% of the positives and flags 5% of the negatives, on 100,000 cases.
"""

RECALL, FALSE_POSITIVE_RATE, CASES = 0.90, 0.05, 100_000

print("positives  flagged  true positives  precision  accuracy")
for share in [0.5, 0.1, 0.01, 0.001]:
    positives = round(CASES * share)
    negatives = CASES - positives
    tp = round(RECALL * positives)
    fp = round(FALSE_POSITIVE_RATE * negatives)
    accuracy = (tp + negatives - fp) / CASES
    print(f"{share:9.1%}  {tp + fp:7}  {tp:14}  {tp / (tp + fp):9.3f}  {accuracy:8.3f}")
