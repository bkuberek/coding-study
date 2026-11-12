import heapq

UNKNOWN = "<unknown>"
FORCES = "forces-replacement"


def reference(value: str) -> tuple[str, str] | None:
    """The target address and attribute of a `${type.name.attribute}` value, else None."""
    if not (value.startswith("${") and value.endswith("}")):
        return None
    kind, name, attribute = value[2:-1].split(".")
    return f"{kind}.{name}", attribute


def kind_of(address: str) -> str:
    return address.split(".", 1)[0]


class Step:
    def __init__(self, verb: str, address: str, tag: str, rank: int) -> None:
        self.verb = verb
        self.address = address
        self.tag = tag
        self.rank = rank
        self.mode = ""
        self.diff: list[list[str]] = []
        self.before: list[Step] = []
        self.after: list[Step] = []

    def row(self) -> list[str]:
        return [self.verb, self.address, *([self.tag] if self.tag else [])]


class PlanEngine:
    """Desired and actual resources are maps of attributes. A plan resolves the references of
    the desired resources in dependency order, which tells for each resource whether it is
    created, updated, replaced, left alone or deleted, then turns those actions into steps joined
    by before-rules and lists the steps in the smallest order by (rank, address) that keeps every
    rule. Apply walks the same steps, skips those behind a failure, and records the state after
    each step that succeeds."""

    def __init__(self) -> None:
        self._desired: dict[str, dict[str, str]] = {}
        self._current: dict[str, dict[str, str]] = {}
        self._deps: dict[str, set[str]] = {}
        self._old: dict[str, dict[str, str]] = {}
        self._old_deps: dict[str, set[str]] = {}
        self._forces: set[tuple[str, str]] = set()
        self._computed: dict[str, set[str]] = {}
        self._marked: set[str] = set()

    # Level 1
    def desire(self, address: str, attributes: list[list[str]]) -> bool:
        new = address not in self._desired
        self._desired[address] = {key: value for key, value in attributes}
        return new

    def remove(self, address: str) -> bool:
        return self._desired.pop(address, None) is not None

    def observe(self, address: str, attributes: list[list[str]]) -> bool:
        new = address not in self._current
        self._current[address] = {key: value for key, value in attributes}
        return new

    def plan(self) -> list[list[str]]:
        errors, steps = self._build()
        if errors:
            return errors
        rows: list[list[str]] = []
        for step in steps:
            rows.append(step.row())
            rows.extend(step.diff)
        return rows

    # Level 2
    def observe_dependency(self, address: str, depends_on: str) -> bool:
        if address not in self._current or depends_on not in self._current:
            return False
        links = self._deps.setdefault(address, set())
        if depends_on in links:
            return False
        links.add(depends_on)
        return True

    # Level 3
    def force_replacement(self, resource_type: str, key: str) -> bool:
        if (resource_type, key) in self._forces:
            return False
        self._forces.add((resource_type, key))
        return True

    def computed(self, resource_type: str, key: str) -> bool:
        names = self._computed.setdefault(resource_type, set())
        if key in names:
            return False
        names.add(key)
        return True

    def create_before_destroy(self, address: str) -> bool:
        if address in self._marked:
            return False
        self._marked.add(address)
        return True

    # Level 4
    def apply(self, failures: list[list[str]], values: list[list[str]]) -> list[list[str]]:
        errors, steps = self._build()
        if errors:
            return errors
        failing = {(verb, address) for verb, address in failures}
        assigned = {(address, attribute): value for address, attribute, value in values}
        status: dict[int, str] = {}
        rows = []
        for step in steps:
            if any(status[id(prior)] != "ok" for prior in step.before):
                outcome = "skipped"
            elif step.verb != "no-op" and (step.verb, step.address) in failing:
                outcome = "failed"
            else:
                outcome = "ok"
                self._perform(step, assigned)
            status[id(step)] = outcome
            rows.append([step.verb, step.address, outcome])
        return rows

    def state(self) -> list[list[str]]:
        rows = []
        for address in sorted(self._current.keys() | self._old.keys()):
            for role, objects in (("current", self._current), ("old", self._old)):
                if address in objects:
                    flat = [part for key in sorted(objects[address]) for part in (key, objects[address][key])]
                    rows.append([address, role, *flat])
        return rows

    # Planning
    def _is_computed(self, address: str, attribute: str) -> bool:
        return attribute in self._computed.get(kind_of(address), ())

    def _links(self) -> tuple[list[list[str]], dict[str, set[str]]]:
        """The unknown references, as error rows, and the dependencies of the desired resources."""
        errors = []
        needs: dict[str, set[str]] = {address: set() for address in self._desired}
        for address in sorted(self._desired):
            for key in sorted(self._desired[address]):
                target = reference(self._desired[address][key])
                if target is None:
                    continue
                other, attribute = target
                if other in self._desired and (
                    attribute in self._desired[other] or self._is_computed(other, attribute)
                ):
                    needs[address].add(other)
                else:
                    errors.append(
                        ["error", "unknown-reference", address, key, f"{other}.{attribute}"]
                    )
        return errors, needs

    @staticmethod
    def _cycles(needs: dict[str, set[str]]) -> list[list[str]]:
        reach = {}
        for start in needs:
            seen: set[str] = set()
            stack = list(needs[start])
            while stack:
                node = stack.pop()
                if node not in seen:
                    seen.add(node)
                    stack.extend(needs[node])
            reach[start] = seen
        groups = set()
        for node in needs:
            if node in reach[node]:
                groups.add(tuple(sorted(other for other in reach[node] if node in reach[other])))
        return [["error", "cycle", *group] for group in sorted(groups)]

    @staticmethod
    def _dependency_order(needs: dict[str, set[str]]) -> list[str]:
        waiting = {address: len(targets) for address, targets in needs.items()}
        users: dict[str, list[str]] = {address: [] for address in needs}
        for address, targets in needs.items():
            for target in targets:
                users[target].append(address)
        ready = sorted(address for address, count in waiting.items() if count == 0)
        heapq.heapify(ready)
        order = []
        while ready:
            address = heapq.heappop(ready)
            order.append(address)
            for user in users[address]:
                waiting[user] -= 1
                if waiting[user] == 0:
                    heapq.heappush(ready, user)
        return order

    def _create_before_destroy(self, needs: dict[str, set[str]]) -> set[str]:
        found: set[str] = set()
        stack = [address for address in self._marked if address in self._desired]
        while stack:
            address = stack.pop()
            if address not in found:
                found.add(address)
                stack.extend(needs[address])
        return found

    def _build(self) -> tuple[list[list[str]], list[Step]]:
        errors, needs = self._links()
        errors += self._cycles(needs)
        if errors:
            return errors, []
        early = self._create_before_destroy(needs)
        action: dict[str, str] = {}
        resolved: dict[str, dict[str, str]] = {}
        applies: dict[str, Step] = {}
        deletes: dict[str, Step] = {}

        for address in self._dependency_order(needs):
            values = {}
            for key, value in self._desired[address].items():
                target = reference(value)
                if target is None:
                    values[key] = value
                elif self._is_computed(*target):
                    other = target[0]
                    replaced = action[other] in ("create", "replace")
                    values[key] = UNKNOWN if replaced else self._current[other][target[1]]
                else:
                    values[key] = resolved[target[0]][target[1]]
            resolved[address] = values
            action[address], step = self._classify(address, values)
            applies[address] = step
            if action[address] == "replace":
                mode = "create-before-destroy" if address in early else "destroy-before-create"
                deletes[address] = Step("delete", address, "replace", 1)
                deletes[address].mode = mode
        for address, attributes in self._current.items():
            if address not in self._desired:
                deletes[address] = Step("delete", address, "", 1)
                deletes[address].diff = self._removed(attributes)
        for address, attributes in self._old.items():
            deletes[address] = Step("delete", address, "old", 1)
            deletes[address].diff = self._removed(attributes)

        def link(first: Step, second: Step) -> None:
            first.after.append(second)
            second.before.append(first)

        for address, targets in needs.items():
            for target in targets:
                link(applies[target], applies[address])
        for address, step in deletes.items():
            held = self._old_deps if step.tag == "old" else self._deps
            for target in held.get(address, ()):
                if target in deletes:
                    link(step, deletes[target])
        for address, step in applies.items():
            if address not in self._current:
                continue
            for target in self._deps.get(address, ()):
                gone = deletes.get(target)
                if gone is not None and gone.mode != "destroy-before-create":
                    link(step, gone)
        for address, step in deletes.items():
            if step.mode == "destroy-before-create":
                link(step, applies[address])
            elif step.mode == "create-before-destroy":
                link(applies[address], step)

        return [], self._order([*applies.values(), *deletes.values()])

    def _classify(self, address: str, values: dict[str, str]) -> tuple[str, Step]:
        computed = sorted(self._computed.get(kind_of(address), ()))
        if address not in self._current:
            step = Step("create", address, "", 0)
            rows = [["+", key, value] for key, value in values.items()]
            rows += [["+", name, UNKNOWN] for name in computed]
            step.diff = sorted(rows, key=lambda row: row[1])
            return "create", step
        actual = {
            key: value
            for key, value in self._current[address].items()
            if not self._is_computed(address, key)
        }
        rows = []
        forced = False
        for key in sorted(values.keys() | actual.keys()):
            before, after = actual.get(key), values.get(key)
            if before == after:
                continue
            if before is None:
                row = ["+", key, after]
            elif after is None:
                row = ["-", key, before]
            else:
                row = ["~", key, before, after]
            if (kind_of(address), key) in self._forces:
                row.append(FORCES)
                forced = True
            rows.append(row)
        if not rows:
            return "no-op", Step("no-op", address, "", 0)
        if not forced:
            step = Step("update", address, "", 0)
            step.diff = rows
            return "update", step
        for name in computed:
            old = self._current[address].get(name)
            rows.append(["+", name, UNKNOWN] if old is None else ["~", name, old, UNKNOWN])
        step = Step("create", address, "replace", 0)
        step.diff = sorted(rows, key=lambda row: row[1])
        return "replace", step

    @staticmethod
    def _removed(attributes: dict[str, str]) -> list[list[str]]:
        return [["-", key, attributes[key]] for key in sorted(attributes)]

    @staticmethod
    def _order(steps: list[Step]) -> list[Step]:
        waiting = {id(step): len(step.before) for step in steps}
        ready = [(step.rank, step.address, id(step), step) for step in steps if not step.before]
        heapq.heapify(ready)
        order = []
        while ready:
            *_, step = heapq.heappop(ready)
            order.append(step)
            for later in step.after:
                waiting[id(later)] -= 1
                if waiting[id(later)] == 0:
                    heapq.heappush(ready, (later.rank, later.address, id(later), later))
        return order

    # Applying
    def _live(self, address: str, key: str) -> str:
        value = self._desired[address][key]
        target = reference(value)
        if target is None:
            return value
        if self._is_computed(*target):
            return self._current[target[0]][target[1]]
        return self._live(*target)

    def _built(self, address: str, assigned: dict[tuple[str, str], str]) -> dict[str, str]:
        made = {key: self._live(address, key) for key in self._desired[address]}
        for name in self._computed.get(kind_of(address), ()):
            made[name] = assigned[(address, name)]
        return made

    def _perform(self, step: Step, assigned: dict[tuple[str, str], str]) -> None:
        address = step.address
        needs = set()
        if address in self._desired:
            needs = {
                target[0]
                for value in self._desired[address].values()
                if (target := reference(value)) is not None
            }
        if step.verb == "create":
            if step.tag == "replace" and address in self._current:
                self._old[address] = self._current[address]
                self._old_deps[address] = self._deps.get(address, set())
            self._current[address] = self._built(address, assigned)
            self._deps[address] = needs
        elif step.verb == "update":
            kept = {
                key: value
                for key, value in self._current[address].items()
                if self._is_computed(address, key)
            }
            made = {key: self._live(address, key) for key in self._desired[address]}
            self._current[address] = {**made, **kept}
            self._deps[address] = needs
        elif step.verb == "delete":
            if step.tag == "old" or step.mode == "create-before-destroy":
                self._old.pop(address, None)
                self._old_deps.pop(address, None)
            else:
                self._current.pop(address, None)
                self._deps.pop(address, None)
