"""Accept any order that takes every course once and each prerequisite before its course,
or [] exactly when no such order exists.

An empty answer is accepted only if the prerequisites contain a cycle, which the checker
decides with its own count of courses whose prerequisites can all be taken (Kahn's method).
"""

from collections import deque


def _has_order(num_courses: int, prerequisites: list[list[int]]) -> bool:
    unlocks: list[list[int]] = [[] for _ in range(num_courses)]
    waiting = [0] * num_courses
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
    return taken == num_courses


def check(case_input: dict, output: object, expected: object | None) -> str | None:
    num_courses = case_input["numCourses"]
    prerequisites = case_input["prerequisites"]
    if not isinstance(output, list) or not all(type(course) is int for course in output):
        return f"expected a list of course numbers, got {output!r}"[:200]
    if not output:
        if _has_order(num_courses, prerequisites):
            return "returned [], but an order that respects every prerequisite exists"
        return None
    if sorted(output) != list(range(num_courses)):
        return f"the order must list each course from 0 to {num_courses - 1} exactly once"
    position = {course: index for index, course in enumerate(output)}
    for course, before in prerequisites:
        if position[before] > position[course]:
            return f"course {course} is taken before its prerequisite {before}"
    return None
