from collections import deque


def can_finish(num_courses: int, prerequisites: list[list[int]]) -> bool:
    unlocks: list[list[int]] = [[] for _ in range(num_courses)]
    waiting = [0] * num_courses  # prerequisites each course still waits for
    for course, before in prerequisites:
        unlocks[before].append(course)
        waiting[course] += 1
    ready = deque(course for course in range(num_courses) if waiting[course] == 0)
    taken = 0
    while ready:
        course = ready.popleft()
        taken += 1
        for unlocked in unlocks[course]:
            waiting[unlocked] -= 1
            if waiting[unlocked] == 0:
                ready.append(unlocked)
    # Courses never taken wait, directly or not, on a cycle.
    return taken == num_courses
