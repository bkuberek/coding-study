"""A first-in, first-out job queue that can also cancel any waiting job in O(1).

A list alone cancels in O(n): it must search for the job and shift what follows. A hash map from
job id to a node of a doubly linked list finds the node in O(1), and the node unlinks itself in
O(1), because it knows both of its neighbors.
"""


class Node:
    def __init__(self, job: str) -> None:
        self.job = job
        self.before: Node | None = None
        self.after: Node | None = None


class JobQueue:
    def __init__(self) -> None:
        self.head = Node("<head>")  # sentinels: every real node has two neighbors
        self.tail = Node("<tail>")
        self.head.after, self.tail.before = self.tail, self.head
        self.nodes: dict[str, Node] = {}

    def submit(self, job: str) -> bool:
        if job in self.nodes:  # one node per id, or the map would lose the first one
            return False
        node = Node(job)
        last = self.tail.before
        assert last is not None
        node.before, node.after = last, self.tail
        last.after = self.tail.before = node
        self.nodes[job] = node
        return True

    def cancel(self, job: str) -> bool:
        node = self.nodes.pop(job, None)
        if node is None:
            return False
        assert node.before is not None and node.after is not None
        node.before.after, node.after.before = node.after, node.before
        return True

    def take(self) -> str | None:
        first = self.head.after
        if first is self.tail or first is None:
            return None
        self.cancel(first.job)
        return first.job

    def waiting(self) -> list[str]:
        jobs, node = [], self.head.after
        while node is not None and node is not self.tail:
            jobs.append(node.job)
            node = node.after
        return jobs


queue = JobQueue()
for job in ("backup", "resize", "email", "report"):
    queue.submit(job)
print("waiting:", queue.waiting())
print("cancel email:", queue.cancel("email"), "->", queue.waiting())
print("cancel email again:", queue.cancel("email"))
print("take:", queue.take(), "->", queue.waiting())
print("submit resize again:", queue.submit("resize"), "->", queue.waiting())
queue.submit("email")
print("submit email:", queue.waiting())
