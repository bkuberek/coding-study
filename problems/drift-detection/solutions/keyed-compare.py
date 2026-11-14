def glob(pattern: str, text: str) -> bool:
    """Whether `text` matches `pattern`, where `*` stands for any run of characters. Walks both
    texts once, and on a mismatch goes back to the last `*` and lets it swallow one more
    character."""
    p = t = 0
    star, mark = -1, 0
    while t < len(text):
        if p < len(pattern) and pattern[p] != "*" and pattern[p] == text[t]:
            p += 1
            t += 1
        elif p < len(pattern) and pattern[p] == "*":
            star, mark = p, t
            p += 1
        elif star >= 0:
            mark += 1
            p, t = star + 1, mark
        else:
            return False
    while p < len(pattern) and pattern[p] == "*":
        p += 1
    return p == len(pattern)


def kind_of(address: str) -> str:
    return address.split(".", 1)[0]


class DriftDetector:
    """The recorded state maps an address to an id and attributes, and a scan maps an id to a type
    and attributes. Drift is found by looking each recorded id up in the scan, comparing values
    after the type's normalization rules, and filtering the rows through the ignore rules. Import
    adds a recorded entry, the plan compares the desired state with the recorded one, and a
    reconcile turns each drift row into the action of the newest policy that matches."""

    def __init__(self) -> None:
        self._recorded: dict[str, tuple[str, dict[str, str]]] = {}
        self._observed: dict[str, tuple[str, dict[str, str]]] = {}
        self._ignores: set[tuple[str, str]] = set()
        self._unordered: set[tuple[str, str]] = set()
        self._defaults: dict[tuple[str, str], str] = {}
        self._desired: dict[str, dict[str, str]] = {}
        self._policies: dict[str, str] = {}

    # Level 1
    def record(self, address: str, resource_id: str, attributes: list[list[str]]) -> bool:
        new = address not in self._recorded
        self._recorded[address] = (resource_id, {key: value for key, value in attributes})
        return new

    def observe(self, resource_id: str, resource_type: str, attributes: list[list[str]]) -> bool:
        new = resource_id not in self._observed
        self._observed[resource_id] = (resource_type, {key: value for key, value in attributes})
        return new

    def drift(self) -> list[list[str]]:
        return [row for row, _ in self._drift_rows()]

    # Level 2
    def ignore(self, pattern: str, key: str) -> bool:
        if (pattern, key) in self._ignores:
            return False
        self._ignores.add((pattern, key))
        return True

    def unordered(self, resource_type: str, key: str) -> bool:
        if (resource_type, key) in self._unordered:
            return False
        self._unordered.add((resource_type, key))
        return True

    def default_value(self, resource_type: str, key: str, value: str) -> bool:
        new = (resource_type, key) not in self._defaults
        self._defaults[(resource_type, key)] = value
        return new

    # Level 3
    def import_resource(self, address: str, resource_id: str) -> str:
        if resource_id not in self._observed:
            return "not-found"
        resource_type, attributes = self._observed[resource_id]
        if kind_of(address) != resource_type:
            return "type-mismatch"
        if any(held == resource_id for held, _ in self._recorded.values()):
            return "already-managed"
        if address in self._recorded:
            return "address-taken"
        self._recorded[address] = (resource_id, dict(attributes))
        return "imported"

    def desire(self, address: str, attributes: list[list[str]]) -> bool:
        new = address not in self._desired
        self._desired[address] = {key: value for key, value in attributes}
        return new

    def plan(self) -> list[list[str]]:
        rows = []
        for address in sorted(self._desired.keys() | self._recorded.keys()):
            if address not in self._recorded:
                rows.append(["create", address])
            elif address not in self._desired:
                rows.append(["delete", address])
            else:
                recorded = self._recorded[address][1]
                desired = self._desired[address]
                for key in self._differing(kind_of(address), recorded, desired):
                    rows.append(["update", address, key, recorded.get(key, ""), desired.get(key, "")])
        return rows

    # Level 4
    def policy(self, pattern: str, mode: str) -> bool:
        new = pattern not in self._policies
        self._policies.pop(pattern, None)
        self._policies[pattern] = mode
        return new

    def reconcile(self) -> list[list[str]]:
        rows = []
        for row, address in self._drift_rows():
            if row[0] == "unmanaged":
                rows.append(["alert-unmanaged", row[1], row[2]])
                continue
            mode = self._mode(address)
            if row[0] == "deleted":
                action = {"revert": "recreate", "accept": "forget"}.get(mode)
                rows.append([action, address] if action else ["alert-deleted", address, row[2]])
                continue
            _, _, key, recorded, observed = row
            if mode == "alert":
                rows.append(["alert", address, key, recorded, observed])
                continue
            desired = self._desired[address].get(key, "")
            if self._same(kind_of(address), key, observed or None, desired or None):
                continue
            if mode == "revert":
                rows.append(["revert", address, key, observed, desired])
            else:
                rows.append(["accept", address, key, desired, observed])
        return rows

    # Comparing
    def _same(self, resource_type: str, key: str, first: str | None, second: str | None) -> bool:
        default = self._defaults.get((resource_type, key))
        first = default if first is None else first
        second = default if second is None else second
        if first is None or second is None:
            return first is second
        if (resource_type, key) in self._unordered:
            return sorted(first.split(",")) == sorted(second.split(","))
        return first == second

    def _differing(self, resource_type: str, first: dict[str, str], second: dict[str, str]) -> list[str]:
        return [
            key
            for key in sorted(first.keys() | second.keys())
            if not self._same(resource_type, key, first.get(key), second.get(key))
        ]

    def _ignored(self, text: str, key: str) -> bool:
        return any(rule_key == key and glob(pattern, text) for pattern, rule_key in self._ignores)

    def _mode(self, address: str) -> str:
        mode = "alert"
        for pattern, rule in self._policies.items():
            if glob(pattern, address):
                mode = rule
        return mode

    def _drift_rows(self) -> list[tuple[list[str], str]]:
        """The drift rows, each with the address it is about ("" for an unmanaged resource)."""
        rows = []
        managed = set()
        for address in sorted(self._recorded):
            resource_id, recorded = self._recorded[address]
            managed.add(resource_id)
            if self._ignored(address, "*"):
                continue
            if resource_id not in self._observed:
                rows.append((["deleted", address, resource_id], address))
                continue
            observed = self._observed[resource_id][1]
            for key in self._differing(kind_of(address), recorded, observed):
                if not self._ignored(address, key):
                    row = ["changed", address, key, recorded.get(key, ""), observed.get(key, "")]
                    rows.append((row, address))
        for resource_id in sorted(self._observed.keys() - managed):
            resource_type = self._observed[resource_id][0]
            if not self._ignored(f"{resource_type}.{resource_id}", "*"):
                rows.append((["unmanaged", resource_id, resource_type], ""))
        return rows
