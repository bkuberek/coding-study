ON_PATH = -1  # marks a course whose chain length is still being computed


def minimum_semesters(n: int, relations: list[list[int]]) -> int:
    required: list[list[int]] = [[] for _ in range(n + 1)]
    for before, after in relations:
        required[after].append(before)
    # chain[c]: courses on the longest prerequisite chain ending at c; 0 = not computed yet.
    chain = [0] * (n + 1)

    def chain_length(course: int) -> int:
        """Longest chain ending at course, or -1 if its prerequisites loop."""
        if chain[course] == ON_PATH:
            return -1
        if chain[course] > 0:
            return chain[course]
        chain[course] = ON_PATH
        longest = 0
        for before in required[course]:
            length = chain_length(before)
            if length < 0:
                return -1
            longest = max(longest, length)
        chain[course] = longest + 1
        return chain[course]

    semesters = 0
    for course in range(1, n + 1):
        length = chain_length(course)
        if length < 0:
            return -1
        semesters = max(semesters, length)
    return semesters
