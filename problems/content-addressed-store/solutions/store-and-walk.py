import hashlib

FIXED_SIZE = 64
WINDOW = 16
BASE = 257
MODULUS = 1_000_000_007
MIN_CHUNK = 32
MAX_CHUNK = 256
DIVISOR = 64
KINDS = ("blob", "tree", "manifest")

Entry = tuple[str, str]


def address_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Damaged(Exception):
    """A tree or a manifest that had to be opened is missing or damaged."""


def fixed_sizes(length: int) -> list[int]:
    return [min(FIXED_SIZE, length - start) for start in range(0, length, FIXED_SIZE)]


def cdc_sizes(data: bytes) -> list[int]:
    """Content-defined cuts: a rolling hash of the last 16 bytes, rolled once per byte."""
    leaving_weight = pow(BASE, WINDOW - 1, MODULUS)
    sizes: list[int] = []
    window_hash, start = 0, 0
    for index, byte in enumerate(data):
        if index >= WINDOW:
            window_hash = (window_hash - data[index - WINDOW] * leaving_weight) % MODULUS
        window_hash = (window_hash * BASE + byte) % MODULUS
        length = index - start + 1
        if length == MAX_CHUNK or (length >= MIN_CHUNK and window_hash % DIVISOR == 0):
            sizes.append(length)
            start = index + 1
    if start < len(data):
        sizes.append(len(data) - start)
    return sizes


class ContentStore:
    """Objects are bytes filed under the SHA-256 digest of those bytes. Every read hashes what it
    finds again, so a damaged object reads as a missing one. Folders and manifests are objects
    that list other objects by address, and refs name the objects the collector keeps."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._file_bytes = {"fixed": 0, "cdc": 0}
        self._chunk_sizes: dict[str, dict[str, int]] = {"fixed": {}, "cdc": {}}
        self._refs: dict[str, Entry] = {}

    def _write(self, data: bytes) -> str:
        address = address_of(data)
        if self._read(address) is None:
            self._objects[address] = data
        return address

    def _read(self, address: str) -> bytes | None:
        data = self._objects.get(address)
        if data is None or address_of(data) != address:
            return None
        return data

    # Level 1
    def put(self, data: str) -> str:
        return self._write(data.encode("utf-8"))

    def get(self, address: str) -> str:
        data = self._read(address)
        return "" if data is None else data.decode("utf-8")

    def check(self, address: str) -> str:
        if address not in self._objects:
            return "missing"
        return "ok" if self._read(address) is not None else "damaged"

    def damage(self, address: str, data: str) -> bool:
        if address not in self._objects:
            return False
        self._objects[address] = data.encode("utf-8")
        return True

    def count(self) -> int:
        return len(self._objects)

    def bytes_stored(self) -> int:
        return sum(len(data) for data in self._objects.values())

    # Level 2
    def snapshot(self, files: list[list[str]]) -> str:
        return self._folder([(path.split("/"), data) for path, data in files])

    def _folder(self, files: list[tuple[list[str], str]]) -> str:
        entries: dict[str, Entry] = {}
        below: dict[str, list[tuple[list[str], str]]] = {}
        for names, data in files:
            if len(names) == 1:
                entries[names[0]] = ("blob", self.put(data))
            else:
                below.setdefault(names[0], []).append((names[1:], data))
        for name, inner in below.items():
            entries[name] = ("tree", self._folder(inner))
        lines = (f"{kind} {address} {name}\n" for name, (kind, address) in sorted(entries.items()))
        return self.put("".join(lines))

    def _open_tree(self, address: str) -> dict[str, Entry]:
        data = self._read(address)
        if data is None:
            raise Damaged(address)
        entries = {}
        for line in data.decode("utf-8").splitlines():
            kind, child, name = line.split(" ", 2)
            entries[name] = (kind, child)
        return entries

    def read_path(self, root: str, path: str) -> str:
        kind, address = "tree", root
        try:
            for name in path.split("/"):
                if kind != "tree":
                    return ""
                entries = self._open_tree(address)
                if name not in entries:
                    return ""
                kind, address = entries[name]
        except Damaged:
            return ""
        return self.get(address) if kind == "blob" else ""

    def diff(self, old_root: str, new_root: str) -> list[str]:
        changes: list[tuple[str, str]] = []
        try:
            self._compare("", old_root, new_root, changes)
        except Damaged:
            return []
        return [f"{op} {path}" for path, op in sorted(changes)]

    def _compare(self, prefix: str, old: str, new: str, changes: list[tuple[str, str]]) -> None:
        if old == new:
            return
        before, after = self._open_tree(old), self._open_tree(new)
        for name in before.keys() | after.keys():
            path = prefix + name
            was, now = before.get(name), after.get(name)
            if was == now:
                continue
            if was and now and was[0] == now[0] == "blob":
                changes.append((path, "M"))
            elif was and now and was[0] == now[0] == "tree":
                self._compare(path + "/", was[1], now[1], changes)
            else:
                if was:
                    self._list_files("D", path, was, changes)
                if now:
                    self._list_files("A", path, now, changes)

    def _list_files(self, op: str, path: str, entry: Entry, changes: list[tuple[str, str]]) -> None:
        kind, address = entry
        if kind == "blob":
            changes.append((path, op))
            return
        for name, inner in self._open_tree(address).items():
            self._list_files(op, f"{path}/{name}", inner, changes)

    # Level 3
    def chunk_sizes(self, data: str, method: str) -> list[int]:
        raw = data.encode("utf-8")
        return fixed_sizes(len(raw)) if method == "fixed" else cdc_sizes(raw)

    def put_file(self, data: str, method: str) -> str:
        raw = data.encode("utf-8")
        lines, start = [], 0
        for size in self.chunk_sizes(data, method):
            address = self._write(raw[start : start + size])
            self._chunk_sizes[method][address] = size
            lines.append(f"{address}\n")
            start += size
        self._file_bytes[method] += len(raw)
        return self.put("".join(lines))

    def read_file(self, manifest: str) -> str:
        listing = self._read(manifest)
        if listing is None:
            return ""
        parts = []
        for address in listing.decode("utf-8").splitlines():
            chunk = self._read(address)
            if chunk is None:
                return ""
            parts.append(chunk)
        return b"".join(parts).decode("utf-8")

    def dedup_ratio(self, method: str) -> float:
        stored = sum(self._chunk_sizes[method].values())
        return self._file_bytes[method] / stored if stored else 0.0

    # Level 4
    def set_ref(self, name: str, kind: str, address: str) -> bool:
        if kind not in KINDS or address not in self._objects:
            return False
        self._refs[name] = (kind, address)
        return True

    def get_ref(self, name: str) -> str:
        return self._refs[name][1] if name in self._refs else ""

    def delete_ref(self, name: str) -> bool:
        return self._refs.pop(name, None) is not None

    def collect_garbage(self) -> int:
        try:
            live = self._mark()
        except Damaged:
            return -1
        dead = [address for address in self._objects if address not in live]
        freed = sum(len(self._objects[address]) for address in dead)
        for address in dead:
            del self._objects[address]
        return freed

    def _mark(self) -> set[str]:
        live: set[str] = set()
        visited: set[Entry] = set()
        pending = list(self._refs.values())
        while pending:
            entry = pending.pop()
            if entry in visited:
                continue
            visited.add(entry)
            kind, address = entry
            live.add(address)
            if kind == "tree":
                pending.extend(self._open_tree(address).values())
            elif kind == "manifest":
                listing = self._read(address)
                if listing is None:
                    raise Damaged(address)
                pending.extend(("blob", line) for line in listing.decode("utf-8").splitlines())
        return live
