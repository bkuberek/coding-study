UNVISITED, ON_PATH, DONE = 0, 1, 2


def can_finish(num_courses: int, prerequisites: list[list[int]]) -> bool:
    required: list[list[int]] = [[] for _ in range(num_courses)]
    for course, before in prerequisites:
        required[course].append(before)
    state = [UNVISITED] * num_courses

    def completes(course: int) -> bool:
        """Whether every prerequisite chain below course ends without looping."""
        state[course] = ON_PATH
        for before in required[course]:
            if state[before] == ON_PATH:
                return False  # the chain came back to a course still being explored
            if state[before] == UNVISITED and not completes(before):
                return False
        state[course] = DONE
        return True

    return all(state[course] == DONE or completes(course) for course in range(num_courses))
