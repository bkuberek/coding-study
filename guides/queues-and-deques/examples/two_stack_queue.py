"""A first-in, first-out queue made of two stacks, and what it costs.

New items are pushed on `inbox`. `outbox` holds items in queue order, the oldest on top. Only when
`outbox` is empty does a dequeue move all of `inbox` across, which reverses it: the oldest on top.
"""

from collections import deque


class TwoStackQueue:
    def __init__(self) -> None:
        self.inbox: list[object] = []
        self.outbox: list[object] = []
        self.stack_operations = 0  # every push and pop on either stack, to measure the cost

    def enqueue(self, item: object) -> None:
        self.inbox.append(item)
        self.stack_operations += 1

    def dequeue(self) -> object:
        if not self.outbox:
            while self.inbox:
                self.outbox.append(self.inbox.pop())
                self.stack_operations += 2
        self.stack_operations += 1
        return self.outbox.pop()  # IndexError when both stacks are empty


class EagerQueue(TwoStackQueue):
    """A broken variant: it moves `inbox` across even when `outbox` still holds older items."""

    def dequeue(self) -> object:
        while self.inbox:
            self.outbox.append(self.inbox.pop())
        return self.outbox.pop()


queue = TwoStackQueue()
for step in ["enqueue a", "enqueue b", "enqueue c", "dequeue", "enqueue d", "dequeue", "dequeue"]:
    if step == "dequeue":
        step += f" -> {queue.dequeue()}"
    else:
        queue.enqueue(step.split()[1])
    print(f"{step:<12} inbox {queue.inbox!s:<17} outbox {queue.outbox}")

eager = EagerQueue()
eager.enqueue("a")
eager.enqueue("b")
first = eager.dequeue()
eager.enqueue("c")
print("eager variant serves:", first, eager.dequeue(), eager.dequeue())

ITEMS = 100_000
queue, reference = TwoStackQueue(), deque()
for item in range(ITEMS):
    queue.enqueue(item)
    reference.append(item)
before = queue.stack_operations
served = [queue.dequeue()]
print(f"first dequeue after {ITEMS:,} enqueues: {queue.stack_operations - before:,} operations")
served += [queue.dequeue() for _ in range(ITEMS - 1)]
print("same order as collections.deque:", served == [reference.popleft() for _ in range(ITEMS)])
print(f"stack operations per item, over its whole life: {queue.stack_operations / ITEMS:.2f}")

queue, served = TwoStackQueue(), []
for item in range(ITEMS):
    queue.enqueue(item)
    if item % 3 == 2:  # two arrivals out of every three are served at once
        served += [queue.dequeue(), queue.dequeue()]
served += [queue.dequeue() for _ in range(ITEMS - len(served))]
print("interleaved, in order:", served == list(range(ITEMS)))
print(f"interleaved, stack operations per item: {queue.stack_operations / ITEMS:.2f}")
