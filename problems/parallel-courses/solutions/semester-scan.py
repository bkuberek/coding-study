def minimum_semesters(n: int, relations: list[list[int]]) -> int:
    required: list[list[int]] = [[] for _ in range(n + 1)]
    for before, after in relations:
        required[after].append(before)
    finished_in = [0] * (n + 1)  # semester a course was taken in; 0 while not taken
    done = 0
    semester = 0
    while done < n:
        semester += 1
        # Free courses need every prerequisite finished in an earlier semester.
        free = [
            course
            for course in range(1, n + 1)
            if finished_in[course] == 0
            and all(0 < finished_in[before] < semester for before in required[course])
        ]
        if not free:
            return -1
        for course in free:
            finished_in[course] = semester
        done += len(free)
    return semester
