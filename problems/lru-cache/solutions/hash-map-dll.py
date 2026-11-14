class _Node:
    __slots__ = ("key", "next", "prev", "value")

    def __init__(self, key: int, value: int) -> None:
        self.key = key
        self.value = value
        self.prev: _Node = self
        self.next: _Node = self


class LRUCache:
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self.nodes: dict[int, _Node] = {}
        # Sentinels: head.next is the least recently used node, tail.prev the most recent.
        self.head = _Node(0, 0)
        self.tail = _Node(0, 0)
        self.head.next = self.tail
        self.tail.prev = self.head

    def get(self, key: int) -> int:
        node = self.nodes.get(key)
        if node is None:
            return -1
        self._unlink(node)
        self._append(node)
        return node.value

    def put(self, key: int, value: int) -> None:
        node = self.nodes.get(key)
        if node is not None:
            node.value = value
            self._unlink(node)
        else:
            if len(self.nodes) == self.capacity:
                oldest = self.head.next
                self._unlink(oldest)
                del self.nodes[oldest.key]
            node = _Node(key, value)
            self.nodes[key] = node
        self._append(node)

    def _unlink(self, node: _Node) -> None:
        node.prev.next = node.next
        node.next.prev = node.prev

    def _append(self, node: _Node) -> None:
        last = self.tail.prev
        last.next = node
        node.prev = last
        node.next = self.tail
        self.tail.prev = node
