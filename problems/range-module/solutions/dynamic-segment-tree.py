EMPTY, COVERED, MIXED = 0, 1, 2
LOW, HIGH = 1, 10**9  # every range lies inside [1, 10^9)
NO_CHILD = -1


class RangeModule:
    """Segment tree over [LOW, HIGH), grown on demand; nodes live in parallel lists.

    A node is EMPTY or COVERED with no children, or MIXED with two children. Nodes whose
    children end up equal are collapsed again, so a node is MIXED exactly when its range is
    partly covered.
    """

    def __init__(self) -> None:
        self.state = [EMPTY]
        self.left = [NO_CHILD]
        self.right = [NO_CHILD]

    def add_range(self, left: int, right: int) -> None:
        self._assign(0, LOW, HIGH, left, right, COVERED)

    def query_range(self, left: int, right: int) -> bool:
        return self._covered(0, LOW, HIGH, left, right)

    def remove_range(self, left: int, right: int) -> None:
        self._assign(0, LOW, HIGH, left, right, EMPTY)

    def _new_node(self, state: int) -> int:
        self.state.append(state)
        self.left.append(NO_CHILD)
        self.right.append(NO_CHILD)
        return len(self.state) - 1

    def _assign(self, node: int, low: int, high: int, left: int, right: int, value: int) -> None:
        if right <= low or high <= left:
            return
        if left <= low and high <= right:
            self.state[node] = value
            self.left[node] = self.right[node] = NO_CHILD
            return
        if self.left[node] == NO_CHILD:
            # A uniform node is split: both halves inherit its state.
            self.left[node] = self._new_node(self.state[node])
            self.right[node] = self._new_node(self.state[node])
        middle = (low + high) // 2
        self._assign(self.left[node], low, middle, left, right, value)
        self._assign(self.right[node], middle, high, left, right, value)
        first, second = self.state[self.left[node]], self.state[self.right[node]]
        if first == second != MIXED:
            self.state[node] = first
            self.left[node] = self.right[node] = NO_CHILD
        else:
            self.state[node] = MIXED

    def _covered(self, node: int, low: int, high: int, left: int, right: int) -> bool:
        if right <= low or high <= left:
            return True
        if self.left[node] == NO_CHILD:
            return self.state[node] == COVERED
        middle = (low + high) // 2
        return self._covered(self.left[node], low, middle, left, right) and self._covered(
            self.right[node], middle, high, left, right
        )
