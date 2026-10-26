def partition(s: str) -> list[list[str]]:
    n = len(s)
    # palindrome[i][j]: whether s[i..j] reads the same both ways. Row i depends on row i + 1.
    palindrome = [[False] * n for _ in range(n)]
    for i in range(n - 1, -1, -1):
        for j in range(i, n):
            palindrome[i][j] = s[i] == s[j] and (j - i < 2 or palindrome[i + 1][j - 1])

    result: list[list[str]] = []
    pieces: list[str] = []

    def cut_from(start: int) -> None:
        if start == n:
            result.append(pieces.copy())
            return
        for end in range(start, n):
            if palindrome[start][end]:
                pieces.append(s[start : end + 1])
                cut_from(end + 1)
                pieces.pop()

    cut_from(0)
    return result
