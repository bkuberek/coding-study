import heapq


class SortingWorkbench:
    """Four classic sorts, each written the way the statement specifies it, with a meter that
    counts the work of the latest sort. A sort returns a new list and never changes its input."""

    def __init__(self) -> None:
        self._meter: list[int] = []

    # Level 1
    def insertion_sort(self, values: list[int]) -> list[int]:
        items = list(values)
        comparisons = 0
        moves = 0
        for i in range(1, len(items)):
            key = items[i]
            j = i - 1
            while j >= 0:
                comparisons += 1
                if items[j] <= key:
                    break
                items[j + 1] = items[j]
                moves += 1
                j -= 1
            items[j + 1] = key
        self._meter = [comparisons, moves]
        return items

    def report(self) -> list[int]:
        return list(self._meter)

    # Level 2
    def merge_sort_by(self, rows: list[list[int]], key: int) -> list[list[int]]:
        self._comparisons = 0
        merged = self._merge_sort(rows, key)
        self._meter = [self._comparisons]
        return [list(row) for row in merged]

    def _merge_sort(self, rows: list[list[int]], key: int) -> list[list[int]]:
        if len(rows) <= 1:
            return list(rows)
        middle = len(rows) // 2
        left = self._merge_sort(rows[:middle], key)
        right = self._merge_sort(rows[middle:], key)
        merged: list[list[int]] = []
        i = j = 0
        while i < len(left) and j < len(right):
            self._comparisons += 1
            if left[i][key] <= right[j][key]:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
        merged.extend(left[i:])
        merged.extend(right[j:])
        return merged

    # Level 3
    def quick_sort(self, values: list[int]) -> list[int]:
        items = list(values)
        calls = 0
        steps = 0
        ranges = [(0, len(items) - 1)]
        while ranges:
            low, high = ranges.pop()
            if high - low < 1:
                continue
            below, above = self._partition(items, low, high)
            calls += 1
            steps += high - low + 1
            ranges.append((low, below - 1))
            ranges.append((above + 1, high))
        self._meter = [calls, steps]
        return items

    def quick_select(self, values: list[int], k: int) -> int:
        items = list(values)
        target = k - 1
        calls = 0
        steps = 0
        low, high = 0, len(items) - 1
        while low < high:
            below, above = self._partition(items, low, high)
            calls += 1
            steps += high - low + 1
            if target < below:
                high = below - 1
            elif target > above:
                low = above + 1
            else:
                break
        self._meter = [calls, steps]
        return items[target]

    @staticmethod
    def _partition(items: list[int], low: int, high: int) -> tuple[int, int]:
        # Afterwards items[low:below] < pivot, items[below:above + 1] == pivot, items[above + 1:high + 1] > pivot.
        pivot = items[low + (high - low) // 2]
        below, i, above = low, low, high
        while i <= above:
            if items[i] < pivot:
                items[below], items[i] = items[i], items[below]
                below += 1
                i += 1
            elif items[i] > pivot:
                items[i], items[above] = items[above], items[i]
                above -= 1
            else:
                i += 1
        return below, above

    # Level 4
    def external_sort(self, values: list[int], memory: int, ways: int) -> list[int]:
        runs = [sorted(values[start : start + memory]) for start in range(0, len(values), memory)]
        initial_runs = len(runs)
        passes = 0
        while len(runs) > 1:
            runs = [self._merge_group(runs[start : start + ways]) for start in range(0, len(runs), ways)]
            passes += 1
        self._meter = [initial_runs, passes]
        return runs[0] if runs else []

    @staticmethod
    def _merge_group(group: list[list[int]]) -> list[int]:
        # The heap holds the front value of each run: (value, run, position in the run).
        heap = [(run[0], index, 0) for index, run in enumerate(group)]
        heapq.heapify(heap)
        merged: list[int] = []
        while heap:
            value, index, position = heapq.heappop(heap)
            merged.append(value)
            if position + 1 < len(group[index]):
                heapq.heappush(heap, (group[index][position + 1], index, position + 1))
        return merged
