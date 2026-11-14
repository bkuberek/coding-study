UNSEEN, ACTIVE, DONE = 0, 1, 2


def find_order(num_courses: int, prerequisites: list[list[int]]) -> list[int]:
    required: list[list[int]] = [[] for _ in range(num_courses)]
    for course, before in prerequisites:
        required[course].append(before)
    state = [UNSEEN] * num_courses
    order = []
    for root in range(num_courses):
        if state[root] != UNSEEN:
            continue
        state[root] = ACTIVE
        stack = [(root, 0)]  # (course, index of the next prerequisite to visit)
        while stack:
            course, next_index = stack[-1]
            if next_index == len(required[course]):
                # Every prerequisite is already in the order: the course can follow them.
                stack.pop()
                state[course] = DONE
                order.append(course)
                continue
            stack[-1] = (course, next_index + 1)
            before = required[course][next_index]
            if state[before] == ACTIVE:
                return []  # the path loops back to a course still being explored
            if state[before] == UNSEEN:
                state[before] = ACTIVE
                stack.append((before, 0))
    return order
