def minimum_semesters(n: int, relations: list[list[int]]) -> int:
    unlocks: list[list[int]] = [[] for _ in range(n + 1)]
    waiting = [0] * (n + 1)
    for before, after in relations:
        unlocks[before].append(after)
        waiting[after] += 1
    semester_courses = [course for course in range(1, n + 1) if waiting[course] == 0]
    semesters = 0
    taken = 0
    while semester_courses:
        semesters += 1
        taken += len(semester_courses)
        next_semester: list[int] = []
        for course in semester_courses:
            for unlocked in unlocks[course]:
                waiting[unlocked] -= 1
                if waiting[unlocked] == 0:
                    next_semester.append(unlocked)
        semester_courses = next_semester
    return semesters if taken == n else -1
