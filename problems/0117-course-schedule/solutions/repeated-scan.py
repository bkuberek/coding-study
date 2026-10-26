def can_finish(num_courses: int, prerequisites: list[list[int]]) -> bool:
    required: list[list[int]] = [[] for _ in range(num_courses)]
    for course, before in prerequisites:
        required[course].append(before)
    taken = [False] * num_courses
    for _ in range(num_courses):
        # Take the first course whose prerequisites are all done; give up if there is none.
        for course in range(num_courses):
            if not taken[course] and all(taken[before] for before in required[course]):
                taken[course] = True
                break
        else:
            return False
    return True
