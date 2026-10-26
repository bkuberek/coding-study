import threading


class _Node:
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: int, value: int) -> None:
        self.key = key
        self.value = value
        self.prev: _Node | None = None
        self.next: _Node | None = None


class LRUCache:
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._nodes: dict[int, _Node] = {}
        self._head = _Node(-1, -1)
        self._tail = _Node(-1, -1)
        self._head.next = self._tail
        self._tail.prev = self._head
        self._lock = threading.Lock()

    def get(self, key: int) -> int:
        with self._lock:
            node = self._nodes.get(key)
            if node is None:
                return -1
            self._unlink(node)
            self._append(node)
            return node.value

    def put(self, key: int, value: int) -> None:
        with self._lock:
            node = self._nodes.get(key)
            if node is not None:
                node.value = value
                self._unlink(node)
                self._append(node)
                return
            if len(self._nodes) == self._capacity:
                eldest = self._head.next
                self._unlink(eldest)
                del self._nodes[eldest.key]
            node = _Node(key, value)
            self._nodes[key] = node
            self._append(node)

    def size(self) -> int:
        with self._lock:
            return len(self._nodes)

    def _unlink(self, node: _Node) -> None:
        node.prev.next = node.next
        node.next.prev = node.prev

    def _append(self, node: _Node) -> None:
        last = self._tail.prev
        last.next = node
        node.prev = last
        node.next = self._tail
        self._tail.prev = node
