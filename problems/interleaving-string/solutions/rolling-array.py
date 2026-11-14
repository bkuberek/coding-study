def is_interleave(s1: str, s2: str, s3: str) -> bool:
    if len(s1) + len(s2) != len(s3):
        return False
    # Swapping the sources does not change the answer, so let the row run along the shorter.
    longer, shorter = (s1, s2) if len(s1) >= len(s2) else (s2, s1)
    # Before row i is processed, reach[j] tells whether longer[:i - 1] and shorter[:j]
    # interleave to s3[:i - 1 + j]; afterwards it holds row i.
    reach = [False] * (len(shorter) + 1)
    for i in range(len(longer) + 1):
        for j in range(len(shorter) + 1):
            if i == 0 and j == 0:
                reach[j] = True
                continue
            from_longer = i > 0 and reach[j] and longer[i - 1] == s3[i + j - 1]
            from_shorter = j > 0 and reach[j - 1] and shorter[j - 1] == s3[i + j - 1]
            reach[j] = from_longer or from_shorter
    return reach[len(shorter)]
