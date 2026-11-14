def find_order(num_courses: int, prerequisites: list[list[int]]) -> list[int]:
    required: list[list[int]] = [[] for _ in range(num_courses)]
    for course, before in prerequisites:
        required[course].append(before)
    taken = [False] * num_courses
    order = []
    for _ in range(num_courses):
        # Take the first course whose prerequisites are all done; give up if there is none.
        for course in range(num_courses):
            if not taken[course] and all(taken[before] for before in required[course]):
                taken[course] = True
                order.append(course)
                break
        else:
            return []
    return order
