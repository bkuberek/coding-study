import re

KEEP, REMOVE, ADD = " ", "-", "+"
HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@$")
OURS, BASE, SEPARATOR, THEIRS = "<<<<<<< ours", "||||||| base", "=======", ">>>>>>> theirs"


class LineDiff:
    def __init__(self) -> None:
        self._patched: list[str] = []

    # Level 1
    def lcs(self, before: list[str], after: list[str]) -> list[str]:
        return [line for kind, line in self._script(before, after) if kind == KEEP]

    def diff(self, before: list[str], after: list[str]) -> list[str]:
        return [kind + line for kind, line in self._script(before, after)]

    def _script(self, before: list[str], after: list[str]) -> list[tuple[str, str]]:
        """The diff with the most kept lines that, read from the top, keeps rather than removes
        and removes rather than adds wherever both stay optimal."""
        n, m = len(before), len(after)
        # longest[i][j]: the length of a longest common subsequence of before[i:] and after[j:].
        longest = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(n - 1, -1, -1):
            for j in range(m - 1, -1, -1):
                if before[i] == after[j]:
                    longest[i][j] = longest[i + 1][j + 1] + 1
                else:
                    longest[i][j] = max(longest[i + 1][j], longest[i][j + 1])
        script = []
        i = j = 0
        while i < n or j < m:
            if i < n and j < m and before[i] == after[j]:
                script.append((KEEP, before[i]))
                i, j = i + 1, j + 1
            elif i < n and (j == m or longest[i + 1][j] >= longest[i][j + 1]):
                script.append((REMOVE, before[i]))
                i += 1
            else:
                script.append((ADD, after[j]))
                j += 1
        return script

    # Level 2
    def unified(self, before: list[str], after: list[str], context: int) -> list[str]:
        script = self._script(before, after)
        changed = [index for index, (kind, _) in enumerate(script) if kind != KEEP]
        if not changed:
            return []
        groups = []
        first = previous = changed[0]
        for index in changed[1:]:
            if index - previous - 1 > 2 * context:
                groups.append((first, previous))
                first = index
            previous = index
        groups.append((first, previous))
        lines = []
        for first, last in groups:
            start, end = max(0, first - context), min(len(script), last + context + 1)
            old_before = sum(kind != ADD for kind, _ in script[:start])
            new_before = sum(kind != REMOVE for kind, _ in script[:start])
            hunk = script[start:end]
            old_count = sum(kind != ADD for kind, _ in hunk)
            new_count = sum(kind != REMOVE for kind, _ in hunk)
            old_range = self._range(old_before, old_count)
            new_range = self._range(new_before, new_count)
            lines.append(f"@@ -{old_range} +{new_range} @@")
            lines.extend(kind + line for kind, line in hunk)
        return lines

    @staticmethod
    def _range(lines_before: int, count: int) -> str:
        if count == 0:
            return f"{lines_before},0"
        if count == 1:
            return f"{lines_before + 1}"
        return f"{lines_before + 1},{count}"

    # Level 3
    def apply_patch(self, lines: list[str], patch: list[str], max_offset: int) -> list[str]:
        result = list(lines)
        statuses = []
        delta = shift = floor = 0
        for start, old, new in self._hunks(patch):
            base = start + delta
            found = self._find(result, old, base + shift, floor, max_offset)
            if found is None:
                statuses.append("rejected")
                continue
            result[found : found + len(old)] = new
            shift = found - base
            delta += len(new) - len(old)
            floor = found + len(new)
            statuses.append(f"applied {shift}")
        self._patched = result
        return statuses

    def patched(self) -> list[str]:
        return list(self._patched)

    @staticmethod
    def _hunks(patch: list[str]) -> list[tuple[int, list[str], list[str]]]:
        """Each hunk as (index where its old lines start, old lines, new lines)."""
        hunks: list[tuple[int, list[str], list[str]]] = []
        for line in patch:
            header = HEADER.match(line)
            if header:
                old_start = int(header.group(1))
                old_count = 1 if header.group(2) is None else int(header.group(2))
                hunks.append((old_start - 1 if old_count > 0 else old_start, [], []))
            elif line.startswith(KEEP):
                hunks[-1][1].append(line[1:])
                hunks[-1][2].append(line[1:])
            elif line.startswith(REMOVE):
                hunks[-1][1].append(line[1:])
            elif line.startswith(ADD):
                hunks[-1][2].append(line[1:])
        return hunks

    @staticmethod
    def _find(
        result: list[str], old: list[str], expected: int, floor: int, max_offset: int
    ) -> int | None:
        """The nearest position to `expected` where `old` matches, the earlier one first."""
        for distance in range(max_offset + 1):
            for position in (expected - distance, expected + distance):
                fits = floor <= position and position + len(old) <= len(result)
                if fits and result[position : position + len(old)] == old:
                    return position
        return None

    # Level 4
    def merge(self, base: list[str], ours: list[str], theirs: list[str]) -> list[str]:
        to_ours = self._kept(base, ours)
        to_theirs = self._kept(base, theirs)
        merged: list[str] = []
        o = a = b = 0
        for index, line in enumerate(base):
            if index in to_ours and index in to_theirs:
                j, k = to_ours[index], to_theirs[index]
                merged.extend(self._resolve(base[o:index], ours[a:j], theirs[b:k]))
                merged.append(line)
                o, a, b = index + 1, j + 1, k + 1
        merged.extend(self._resolve(base[o:], ours[a:], theirs[b:]))
        return merged

    def _kept(self, base: list[str], other: list[str]) -> dict[int, int]:
        """For each line of `base` that the diff to `other` keeps, the index it keeps it at."""
        kept = {}
        i = j = 0
        for kind, _ in self._script(base, other):
            if kind == KEEP:
                kept[i] = j
            i += kind != ADD
            j += kind != REMOVE
        return kept

    @staticmethod
    def _resolve(base: list[str], ours: list[str], theirs: list[str]) -> list[str]:
        if ours == theirs:
            return ours
        if ours == base:
            return theirs
        if theirs == base:
            return ours
        return [OURS, *ours, BASE, *base, SEPARATOR, *theirs, THEIRS]
