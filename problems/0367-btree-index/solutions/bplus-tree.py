from bisect import bisect_left, bisect_right

Key = tuple[int, ...]


class _Leaf:
    __slots__ = ("keys", "next", "rows")

    def __init__(self, keys: list[Key], rows: list[int]) -> None:
        self.keys = keys
        self.rows = rows
        self.next: _Leaf | None = None


class _Inner:
    __slots__ = ("children", "keys")

    def __init__(self, keys: list[Key], children: list["_Leaf | _Inner"]) -> None:
        self.keys = keys
        self.children = children


Node = _Leaf | _Inner


class BTreeIndex:
    """A B+ tree: every entry lives in a leaf, the leaves are linked left to right, and the inner
    nodes hold separator keys that only steer the way down. Keys are tuples, so Python compares
    them field by field, which is exactly the order of a composite key.

    Every change walks down once and keeps the path, then repairs nodes on the way back up:
    splits after an insert, borrows and merges after a remove.
    """

    def __init__(self, min_keys: int) -> None:
        self._d = min_keys
        self._root: Node = _Leaf([], [])

    # Level 1
    def insert(self, key: list[int], row_id: int) -> bool:
        target = tuple(key)
        leaf, path = self._descend(target)
        at = bisect_left(leaf.keys, target)
        if at < len(leaf.keys) and leaf.keys[at] == target:
            return False
        leaf.keys.insert(at, target)
        leaf.rows.insert(at, row_id)
        self._split_upward(leaf, path)
        return True

    def search(self, key: list[int]) -> int:
        target = tuple(key)
        leaf, _ = self._descend(target)
        at = bisect_left(leaf.keys, target)
        if at < len(leaf.keys) and leaf.keys[at] == target:
            return leaf.rows[at]
        return -1

    def levels(self) -> list[str]:
        lines = []
        level: list[Node] = [self._root]
        while level:
            lines.append(" ".join(self._show(node) for node in level))
            level = [child for node in level if isinstance(node, _Inner) for child in node.children]
        return lines

    # Level 2
    def range_scan(self, low: list[int], high: list[int]) -> list[int]:
        return self._scan(tuple(low), tuple(high))[0]

    def scan_visits(self, low: list[int], high: list[int]) -> int:
        return self._scan(tuple(low), tuple(high))[1]

    def height(self) -> int:
        count, node = 1, self._root
        while isinstance(node, _Inner):
            count, node = count + 1, node.children[0]
        return count

    # Level 3
    def remove(self, key: list[int]) -> bool:
        target = tuple(key)
        leaf, path = self._descend(target)
        at = bisect_left(leaf.keys, target)
        if at == len(leaf.keys) or leaf.keys[at] != target:
            return False
        del leaf.keys[at]
        del leaf.rows[at]
        node: Node = leaf
        while path and len(node.keys) < self._d:
            parent, index = path.pop()
            if isinstance(node, _Leaf):
                self._fix_leaf(parent, index)
            else:
                self._fix_inner(parent, index)
            node = parent
        if isinstance(self._root, _Inner) and not self._root.keys:
            self._root = self._root.children[0]
        return True

    # Level 4
    def bulk_load(self, keys: list[list[int]], row_ids: list[int], fill_percent: int) -> bool:
        if isinstance(self._root, _Inner) or self._root.keys:
            return False
        sorted_keys = [tuple(key) for key in keys]
        if any(sorted_keys[i] >= sorted_keys[i + 1] for i in range(len(sorted_keys) - 1)):
            return False
        if not sorted_keys:
            return True
        per = 2 * self._d * fill_percent // 100
        leaves: list[Node] = []
        start = 0
        for size in self._sizes(len(sorted_keys), per, self._d, 2 * self._d):
            leaf = _Leaf(sorted_keys[start : start + size], list(row_ids[start : start + size]))
            if leaves:
                leaves[-1].next = leaf  # type: ignore[union-attr]
            leaves.append(leaf)
            start += size
        level = leaves
        lowest = [leaf.keys[0] for leaf in leaves]
        while len(level) > 1:
            parents: list[Node] = []
            parent_lowest: list[Key] = []
            start = 0
            for size in self._sizes(len(level), per + 1, self._d + 1, 2 * self._d + 1):
                children = level[start : start + size]
                parents.append(_Inner(lowest[start + 1 : start + size], children))
                parent_lowest.append(lowest[start])
                start += size
            level, lowest = parents, parent_lowest
        self._root = level[0]
        return True

    def prefix_scan(self, prefix: list[int]) -> list[int]:
        target = tuple(prefix)
        width = len(target)
        node = self._root
        while isinstance(node, _Inner):
            node = node.children[sum(1 for key in node.keys if key[:width] < target)]
        leaf: _Leaf | None = node
        rows = []
        while leaf is not None:
            for key, row in zip(leaf.keys, leaf.rows, strict=True):
                if key[:width] > target:
                    return rows
                if key[:width] == target:
                    rows.append(row)
            leaf = leaf.next
        return rows

    # Helpers
    def _descend(self, key: Key) -> tuple[_Leaf, list[tuple[_Inner, int]]]:
        path = []
        node = self._root
        while isinstance(node, _Inner):
            index = bisect_right(node.keys, key)
            path.append((node, index))
            node = node.children[index]
        return node, path

    def _split_upward(self, leaf: _Leaf, path: list[tuple[_Inner, int]]) -> None:
        d = self._d
        if len(leaf.keys) <= 2 * d:
            return
        right = _Leaf(leaf.keys[d:], leaf.rows[d:])
        del leaf.keys[d:]
        del leaf.rows[d:]
        right.next, leaf.next = leaf.next, right
        left: Node = leaf
        separator, new_node = right.keys[0], right
        while path:
            parent, index = path.pop()
            parent.keys.insert(index, separator)
            parent.children.insert(index + 1, new_node)
            if len(parent.keys) <= 2 * d:
                return
            separator = parent.keys[d]
            new_node = _Inner(parent.keys[d + 1 :], parent.children[d + 1 :])
            del parent.keys[d:]
            del parent.children[d + 1 :]
            left = parent
        self._root = _Inner([separator], [left, new_node])

    def _scan(self, low: Key, high: Key) -> tuple[list[int], int]:
        leaf, path = self._descend(low)
        visits = len(path) + 1
        rows = []
        at = bisect_left(leaf.keys, low)
        while True:
            while at < len(leaf.keys):
                if leaf.keys[at] > high:
                    return rows, visits
                rows.append(leaf.rows[at])
                at += 1
            if leaf.next is None:
                return rows, visits
            leaf, at, visits = leaf.next, 0, visits + 1

    def _fix_leaf(self, parent: _Inner, index: int) -> None:
        node = parent.children[index]
        left = parent.children[index - 1] if index > 0 else None
        right = parent.children[index + 1] if index + 1 < len(parent.children) else None
        assert isinstance(node, _Leaf)
        if isinstance(left, _Leaf) and len(left.keys) > self._d:
            node.keys.insert(0, left.keys.pop())
            node.rows.insert(0, left.rows.pop())
            parent.keys[index - 1] = node.keys[0]
        elif isinstance(right, _Leaf) and len(right.keys) > self._d:
            node.keys.append(right.keys.pop(0))
            node.rows.append(right.rows.pop(0))
            parent.keys[index] = right.keys[0]
        elif isinstance(left, _Leaf):
            left.keys += node.keys
            left.rows += node.rows
            left.next = node.next
            del parent.keys[index - 1]
            del parent.children[index]
        else:
            assert isinstance(right, _Leaf)
            node.keys += right.keys
            node.rows += right.rows
            node.next = right.next
            del parent.keys[index]
            del parent.children[index + 1]

    def _fix_inner(self, parent: _Inner, index: int) -> None:
        node = parent.children[index]
        left = parent.children[index - 1] if index > 0 else None
        right = parent.children[index + 1] if index + 1 < len(parent.children) else None
        assert isinstance(node, _Inner)
        if isinstance(left, _Inner) and len(left.keys) > self._d:
            node.keys.insert(0, parent.keys[index - 1])
            parent.keys[index - 1] = left.keys.pop()
            node.children.insert(0, left.children.pop())
        elif isinstance(right, _Inner) and len(right.keys) > self._d:
            node.keys.append(parent.keys[index])
            parent.keys[index] = right.keys.pop(0)
            node.children.append(right.children.pop(0))
        elif isinstance(left, _Inner):
            left.keys += [parent.keys[index - 1], *node.keys]
            left.children += node.children
            del parent.keys[index - 1]
            del parent.children[index]
        else:
            assert isinstance(right, _Inner)
            node.keys += [parent.keys[index], *right.keys]
            node.children += right.children
            del parent.keys[index]
            del parent.children[index + 1]

    @staticmethod
    def _sizes(total: int, per: int, minimum: int, maximum: int) -> list[int]:
        sizes = [per] * (total // per)
        if total % per:
            sizes.append(total % per)
        if len(sizes) > 1 and sizes[-1] < minimum:
            pool = sizes[-2] + sizes[-1]
            sizes[-2:] = [pool] if pool <= maximum else [(pool + 1) // 2, pool // 2]
        return sizes

    @staticmethod
    def _show(node: Node) -> str:
        return "[" + " ".join(",".join(map(str, key)) for key in node.keys) + "]"
