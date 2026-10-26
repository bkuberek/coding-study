import heapq


def get_order(tasks: list[list[int]]) -> list[int]:
    arrivals = sorted(range(len(tasks)), key=lambda index: tasks[index][0])
    waiting: list[tuple[int, int]] = []  # (processing time, index): ties go to the smaller index
    time = 0
    next_arrival = 0
    order: list[int] = []
    while len(order) < len(tasks):
        if not waiting and time < tasks[arrivals[next_arrival]][0]:
            time = tasks[arrivals[next_arrival]][0]  # idle until the next arrival
        while next_arrival < len(tasks) and tasks[arrivals[next_arrival]][0] <= time:
            index = arrivals[next_arrival]
            heapq.heappush(waiting, (tasks[index][1], index))
            next_arrival += 1
        processing, index = heapq.heappop(waiting)
        time += processing
        order.append(index)
    return order
