"""content-addressed-store promises that its hidden cases catch the classic mistakes of a store
that files data under its digest: addresses of the wrong bytes, sizes counted in characters, a
store that trusts its disk, folder texts that are not canonical, a diff that opens what did not
change, rolling hashes that go negative or overflow, a ratio over the wrong totals, and a collector
that frees shared objects or sweeps after a failed mark. These tests replay every case against a
model of the store written from the statement, which must give every expected output, and against
that model with one mistake planted at a time, which some hidden case must fail. A mistake that
crashes fails its case, as a thrown exception does in the grader. The Rust starter's SHA-256 helper
is the one the Rust reference uses, and its own tests pass against NIST's examples and the digest
of the empty message."""

import contextlib
import hashlib
import json
import math
import re
import shutil
import subprocess
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0322-content-addressed-store"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
RUST_HELPER = PROBLEM / "helpers" / "sha256.rs"
RUST_REFERENCE = PROBLEM / "solutions" / "store-and-walk.rs"
FIXED_SIZE = 64
WINDOW = 16
BASE = 257
MODULUS = 1_000_000_007
MIN_CHUNK = 32
MAX_CHUNK = 256
DIVISOR = 64
KINDS = ("blob", "tree", "manifest")
Entry = tuple[str, str]


class DamagedError(Exception):
    """A tree or a manifest that must be opened is missing or damaged."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def truncated_remainder(value: int, divisor: int) -> int:
    """The `%` of C, Java, Go, Rust and JavaScript: the sign of the dividend."""
    remainder = abs(value) % divisor
    return remainder if value >= 0 else -remainder


def wrap32(value: int) -> int:
    return (value + 2**31) % 2**32 - 2**31


class Model:
    """The store as the statement words it, one rule per method, so that each mistake below
    overrides a single method. Its methods take a call's arguments."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.logical: dict[str, int] = {"fixed": 0, "cdc": 0}
        self.distinct: dict[str, dict[str, int]] = {"fixed": {}, "cdc": {}}
        self.refs: dict[str, Entry] = {}

    # --- objects
    def encode(self, data: str) -> bytes:
        return data.encode("utf-8")

    def decode(self, data: bytes) -> str:
        return data.decode("utf-8")

    def address(self, data: bytes) -> str:
        return sha256_hex(data)

    def size(self, data: bytes) -> int:
        return len(data)

    def intact(self, address: str) -> bool:
        return address in self.objects and sha256_hex(self.objects[address]) == address

    def stores(self, address: str) -> bool:
        """Whether a write finds the address taken: only by an intact object."""
        return self.intact(address)

    def write(self, data: bytes) -> str:
        address = self.address(data)
        if not self.stores(address):
            self.objects[address] = data
        return address

    def read(self, address: str) -> bytes | None:
        return self.objects[address] if self.intact(address) else None

    # --- level 1
    def put(self, data: str) -> str:
        return self.write(self.encode(data))

    def get(self, address: str) -> str:
        data = self.read(address)
        return "" if data is None else self.decode(data)

    def check(self, address: str) -> str:
        if address not in self.objects:
            return "missing"
        return "ok" if self.intact(address) else "damaged"

    def damage(self, address: str, data: str) -> bool:
        if address not in self.objects:
            return False
        self.objects[address] = self.encode(data)
        return True

    def count(self) -> int:
        return len(self.objects)

    def bytes_stored(self) -> int:
        return sum(self.size(data) for data in self.objects.values())

    # --- level 2
    def tree_line(self, kind: str, address: str, name: str) -> str:
        return f"{kind} {address} {name}\n"

    def sort_names(self, entries: Mapping[str, Entry]) -> list[str]:
        return sorted(entries)

    def tree_text(self, entries: Mapping[str, Entry]) -> str:
        return "".join(self.tree_line(*entries[name], name) for name in self.sort_names(entries))

    def folder(self, files: Sequence[tuple[list[str], str]]) -> str:
        entries: dict[str, Entry] = {}
        below: dict[str, list[tuple[list[str], str]]] = {}
        for names, data in files:
            if len(names) == 1:
                entries[names[0]] = ("blob", self.put(data))
            else:
                below.setdefault(names[0], []).append((names[1:], data))
        for name, inner in below.items():
            entries[name] = ("tree", self.folder(inner))
        return self.put(self.tree_text(entries))

    def snapshot(self, files: list[list[str]]) -> str:
        return self.folder([(path.split("/"), data) for path, data in files])

    def parse(self, text: str) -> dict[str, Entry]:
        entries = {}
        for line in text.splitlines():
            kind, address, name = line.split(" ", 2)
            entries[name] = (kind, address)
        return entries

    def open_tree(self, address: str) -> dict[str, Entry]:
        data = self.read(address)
        if data is None:
            raise DamagedError(address)
        return self.parse(self.decode(data))

    def read_path(self, root: str, path: str) -> str:
        kind, address = "tree", root
        try:
            for name in path.split("/"):
                if kind != "tree":
                    return ""
                entries = self.open_tree(address)
                if name not in entries:
                    return ""
                kind, address = entries[name]
        except DamagedError:
            return ""
        return self.get(address) if kind == "blob" else ""

    def diff(self, old_root: str, new_root: str) -> list[str]:
        changes: list[str] = []
        try:
            self.compare("", old_root, new_root, changes)
        except DamagedError:
            return []
        return self.order_changes(changes)

    def order_changes(self, changes: list[str]) -> list[str]:
        return sorted(changes, key=lambda change: change[2:])

    def same_folder(self, old: str, new: str) -> bool:
        return old == new

    def compare(self, prefix: str, old: str, new: str, changes: list[str]) -> None:
        if self.same_folder(old, new):
            return
        before, after = self.open_tree(old), self.open_tree(new)
        for name in sorted(set(before) | set(after)):
            self.compare_entry(prefix + name, before.get(name), after.get(name), changes)

    def compare_entry(
        self, path: str, old: Entry | None, new: Entry | None, changes: list[str]
    ) -> None:
        if old == new:
            return
        if old and new and old[0] == new[0] == "blob":
            changes.append(f"M {path}")
        elif old and new and old[0] == new[0] == "tree":
            self.compare(path + "/", old[1], new[1], changes)
        else:
            if old:
                self.list_files("D", path, old, changes)
            if new:
                self.list_files("A", path, new, changes)

    def list_files(self, op: str, path: str, entry: Entry, changes: list[str]) -> None:
        kind, address = entry
        if kind == "blob":
            changes.append(f"{op} {path}")
            return
        for name, inner in self.open_tree(address).items():
            self.list_files(op, f"{path}/{name}", inner, changes)

    # --- level 3
    def power(self) -> int:
        return pow(BASE, WINDOW - 1, MODULUS)

    def roll(self, value: int, out: int | None, new: int) -> int:
        if out is not None:
            value = (value - out * self.power()) % MODULUS
        return (value * BASE + new) % MODULUS

    def boundary(self, value: int) -> bool:
        return value % DIVISOR == 0

    def window_hashes(self, data: bytes) -> list[int]:
        """The window hash of the 16 bytes ending at each position, rolled from the start."""
        hashes, value = [], 0
        for index, byte in enumerate(data):
            out = data[index - WINDOW] if index >= WINDOW else None
            value = self.roll(value, out, byte)
            hashes.append(value)
        return hashes

    def cut_here(self, length: int, value: int) -> bool:
        return length == MAX_CHUNK or (length >= MIN_CHUNK and self.boundary(value))

    def cdc_sizes(self, data: bytes) -> list[int]:
        hashes = self.window_hashes(data)
        sizes, start = [], 0
        for index in range(len(data)):
            if self.cut_here(index - start + 1, hashes[index]):
                sizes.append(index + 1 - start)
                start = index + 1
        return [*sizes, len(data) - start] if start < len(data) else sizes

    def fixed_sizes(self, data: bytes) -> list[int]:
        return [min(FIXED_SIZE, len(data) - start) for start in range(0, len(data), FIXED_SIZE)]

    def chunk_sizes(self, data: str, method: str) -> list[int]:
        raw = self.encode(data)
        return self.fixed_sizes(raw) if method == "fixed" else self.cdc_sizes(raw)

    def manifest_line(self, address: str, chunk: bytes) -> str:
        return f"{address}\n"

    def remember(self, method: str, data: bytes, chunks: Sequence[tuple[str, bytes]]) -> None:
        self.logical[method] += len(data)
        for address, chunk in chunks:
            self.distinct[method][address] = len(chunk)

    def put_file(self, data: str, method: str) -> str:
        raw, chunks, start = self.encode(data), [], 0
        for size in self.chunk_sizes(data, method):
            chunk = raw[start : start + size]
            chunks.append((self.write(chunk), chunk))
            start += size
        self.remember(method, raw, chunks)
        return self.put("".join(self.manifest_line(address, chunk) for address, chunk in chunks))

    def read_chunk(self, address: str) -> bytes | None:
        return self.read(address)

    def read_file(self, manifest: str) -> str:
        listing = self.read(manifest)
        if listing is None:
            return ""
        parts = []
        for address in self.decode(listing).splitlines():
            chunk = self.read_chunk(address)
            if chunk is None:
                return ""
            parts.append(chunk)
        return self.decode(b"".join(parts))

    def ratio(self, logical: int, stored: int) -> float:
        return logical / stored if stored else 0.0

    def dedup_ratio(self, method: str) -> float:
        return self.ratio(self.logical[method], sum(self.distinct[method].values()))

    # --- level 4
    def set_ref(self, name: str, kind: str, address: str) -> bool:
        if kind not in KINDS or address not in self.objects:
            return False
        self.refs[name] = (kind, address)
        return True

    def get_ref(self, name: str) -> str:
        return self.refs[name][1] if name in self.refs else ""

    def delete_ref(self, name: str) -> bool:
        return self.refs.pop(name, None) is not None

    def roots(self) -> list[Entry]:
        return [self.refs[name] for name in sorted(self.refs)]

    def visit_key(self, kind: str, address: str) -> Entry | str:
        return (kind, address)

    def reached(self, kind: str, address: str) -> list[Entry]:
        """What a live object reaches: the entries of a tree, the chunks of a manifest."""
        if kind == "blob":
            return []
        data = self.read(address)
        if data is None:
            raise DamagedError(address)
        if kind == "tree":
            return list(self.parse(self.decode(data)).values())
        return [("blob", line) for line in self.decode(data).splitlines()]

    def mark(self) -> set[str]:
        live: set[str] = set()
        visited: set[Entry | str] = set()
        pending = list(reversed(self.roots()))
        while pending:
            kind, address = pending.pop()
            key = self.visit_key(kind, address)
            if key in visited:
                continue
            visited.add(key)
            live.add(address)
            pending.extend(reversed(self.reached(kind, address)))
        return live

    def sweep(self, live: set[str]) -> int:
        dead = [address for address in self.objects if address not in live]
        freed = sum(self.size(self.objects[address]) for address in dead)
        for address in dead:
            del self.objects[address]
        return freed

    def collect_garbage(self) -> int:
        try:
            live = self.mark()
        except DamagedError:
            return -1
        return self.sweep(live)


# ------------------------------------------------------------------ level 1 mistakes
class AddressOfUtf16(Model):
    """Hashes the UTF-16 code units of the text, as a string's own bytes in Java or JavaScript."""

    def address(self, data: bytes) -> str:
        return sha256_hex(self.decode(data).encode("utf-16-le"))

    def intact(self, address: str) -> bool:
        return address in self.objects and self.address(self.objects[address]) == address


class AddressInUppercase(Model):
    """Writes the digest with uppercase hexadecimal digits."""

    def address(self, data: bytes) -> str:
        return sha256_hex(data).upper()

    def intact(self, address: str) -> bool:
        return address in self.objects and self.address(self.objects[address]) == address


class TextNormalized(Model):
    """Normalizes text to NFC before storing it."""

    def encode(self, data: str) -> bytes:
        return unicodedata.normalize("NFC", data).encode("utf-8")


class SizeInCharacters(Model):
    """Counts the characters of an object, not its bytes."""

    def size(self, data: bytes) -> int:
        return len(self.decode(data))


class NoDeduplication(Model):
    """Keeps every put as an object of its own."""

    def __init__(self) -> None:
        super().__init__()
        self.copies: list[bytes] = []

    def write(self, data: bytes) -> str:
        self.copies.append(data)
        return super().write(data)

    def count(self) -> int:
        return len(self.copies)

    def bytes_stored(self) -> int:
        return sum(len(data) for data in self.copies)


class TrustsTheDisk(Model):
    """Reads stored bytes without hashing them again."""

    def read(self, address: str) -> bytes | None:
        return self.objects.get(address)


class CheckTrustsTheDisk(Model):
    """`check` says ok for any stored object."""

    def check(self, address: str) -> str:
        return "ok" if address in self.objects else "missing"


class DamageCreatesObjects(Model):
    """Damages an address that holds nothing by storing the data there."""

    def damage(self, address: str, data: str) -> bool:
        self.objects[address] = self.encode(data)
        return True


class DamageRefiles(Model):
    """Files the damaged bytes under their own new address, as a fresh put would."""

    def damage(self, address: str, data: str) -> bool:
        if address not in self.objects:
            return False
        del self.objects[address]
        self.put(data)
        return True


class PutNeverRepairs(Model):
    """Dedup looks for the address only, so a damaged copy stays forever."""

    def stores(self, address: str) -> bool:
        return address in self.objects


class LookupIgnoresCase(Model):
    """Finds an address whatever the case of its letters."""

    def read(self, address: str) -> bytes | None:
        return super().read(address.lower())

    def check(self, address: str) -> str:
        return super().check(address.lower())


class TotalOfOriginalSizes(Model):
    """Keeps the size each object had when it was put, so damage never changes the total."""

    def __init__(self) -> None:
        super().__init__()
        self.sizes: dict[str, int] = {}

    def write(self, data: bytes) -> str:
        address = super().write(data)
        self.sizes[address] = len(data)
        return address

    def bytes_stored(self) -> int:
        return sum(self.sizes[address] for address in self.objects)


# ------------------------------------------------------------------ level 2 mistakes
class EntriesInGivenOrder(Model):
    """Lists a folder's entries in the order the files came."""

    def sort_names(self, entries: Mapping[str, Entry]) -> list[str]:
        return list(entries)


class EntriesSortedWithoutCase(Model):
    """Sorts names without their case."""

    def sort_names(self, entries: Mapping[str, Entry]) -> list[str]:
        return sorted(entries, key=lambda name: (name.lower(), name))


class FoldersFirst(Model):
    """Lists the subfolders before the files."""

    def sort_names(self, entries: Mapping[str, Entry]) -> list[str]:
        return sorted(entries, key=lambda name: (entries[name][0] != "tree", name))


class FoldersSortedWithSlash(Model):
    """Sorts a folder as if its name ended with `/`."""

    def sort_names(self, entries: Mapping[str, Entry]) -> list[str]:
        return sorted(entries, key=lambda name: name + "/" if entries[name][0] == "tree" else name)


class TabBeforeName(Model):
    """Separates the address and the name with a tab."""

    def tree_line(self, kind: str, address: str, name: str) -> str:
        return f"{kind} {address}\t{name}\n"


class NoFinalLineFeed(Model):
    """Joins the lines with line feeds, so the last one has none."""

    def tree_text(self, entries: Mapping[str, Entry]) -> str:
        return super().tree_text(entries).removesuffix("\n")


class FlatTree(Model):
    """Lists every file of the snapshot by its full path in one tree."""

    def snapshot(self, files: list[list[str]]) -> str:
        entries = {path: ("blob", self.put(data)) for path, data in files}
        return self.put(self.tree_text(entries))


class FoldersNotStored(Model):
    """Computes each folder's address but stores only the files."""

    def folder(self, files: Sequence[tuple[list[str], str]]) -> str:
        entries: dict[str, Entry] = {}
        below: dict[str, list[tuple[list[str], str]]] = {}
        for names, data in files:
            if len(names) == 1:
                entries[names[0]] = ("blob", self.put(data))
            else:
                below.setdefault(names[0], []).append((names[1:], data))
        for name, inner in below.items():
            entries[name] = ("tree", self.folder(inner))
        return self.address(self.tree_text(entries).encode("utf-8"))


class ReadPathUnchecked(Model):
    """Follows the path through stored bytes without checking them."""

    def read_path(self, root: str, path: str) -> str:
        kind, address = "tree", root
        for name in path.split("/"):
            data = self.objects.get(address)
            if kind != "tree" or data is None:
                return ""
            entries = self.parse(self.decode(data))
            if name not in entries:
                return ""
            kind, address = entries[name]
        return self.decode(self.objects.get(address, b"")) if kind == "blob" else ""


class ReadPathFlattens(Model):
    """Lists every file of the snapshot first, opening every folder, then looks the path up."""

    def read_path(self, root: str, path: str) -> str:
        files: dict[str, str] = {}
        try:
            self.collect(root, "", files)
        except DamagedError:
            return ""
        return self.get(files[path]) if path in files else ""

    def collect(self, address: str, prefix: str, files: dict[str, str]) -> None:
        for name, (kind, inner) in self.open_tree(address).items():
            if kind == "blob":
                files[prefix + name] = inner
            else:
                self.collect(inner, f"{prefix}{name}/", files)


class ReadPathReturnsFolders(Model):
    """Returns a folder's text when the path ends at a folder."""

    def read_path(self, root: str, path: str) -> str:
        kind, address = "tree", root
        try:
            for name in path.split("/"):
                if kind != "tree":
                    return ""
                entries = self.open_tree(address)
                if name not in entries:
                    return ""
                kind, address = entries[name]
        except DamagedError:
            return ""
        return self.get(address)


class DiffOpensEqualFolders(Model):
    """Walks into every pair of folders, even those with the same address."""

    def same_folder(self, old: str, new: str) -> bool:
        return False

    def compare_entry(
        self, path: str, old: Entry | None, new: Entry | None, changes: list[str]
    ) -> None:
        if old and new and old[0] == new[0] == "tree":
            self.compare(path + "/", old[1], new[1], changes)
        else:
            super().compare_entry(path, old, new, changes)


class DiffUnchecked(Model):
    """Opens folders without checking their bytes."""

    def open_tree(self, address: str) -> dict[str, Entry]:
        if address not in self.objects:
            raise DamagedError(address)
        return self.parse(self.decode(self.objects[address]))


class DiffListsFolders(Model):
    """Reports an added or deleted folder as one entry instead of its files."""

    def list_files(self, op: str, path: str, entry: Entry, changes: list[str]) -> None:
        changes.append(f"{op} {path}")


class DiffModifiesOnKindChange(Model):
    """Reports a file that became a folder, or the reverse, as modified."""

    def compare_entry(
        self, path: str, old: Entry | None, new: Entry | None, changes: list[str]
    ) -> None:
        if old and new and old[0] != new[0]:
            changes.append(f"M {path}")
        else:
            super().compare_entry(path, old, new, changes)


class DiffSortedByKind(Model):
    """Sorts the changes as strings, so by their letter first."""

    def order_changes(self, changes: list[str]) -> list[str]:
        return sorted(changes)


class DiffInWalkOrder(Model):
    """Returns the changes in the order the walk found them."""

    def order_changes(self, changes: list[str]) -> list[str]:
        return changes


class DiffIgnoresDamage(Model):
    """Skips a folder it cannot open instead of answering []."""

    def diff(self, old_root: str, new_root: str) -> list[str]:
        changes: list[str] = []
        self.walk("", old_root, new_root, changes)
        return self.order_changes(changes)

    def walk(self, prefix: str, old: str, new: str, changes: list[str]) -> None:
        try:
            self.compare(prefix, old, new, changes)
        except DamagedError:
            return


# ------------------------------------------------------------------ level 3 mistakes
class FixedDropsTheTail(Model):
    """Keeps only whole 64-byte chunks."""

    def fixed_sizes(self, data: bytes) -> list[int]:
        return [FIXED_SIZE] * (len(data) // FIXED_SIZE)


class EmptyDataHasOneChunk(Model):
    """Gives empty data one chunk of size 0."""

    def chunk_sizes(self, data: str, method: str) -> list[int]:
        return super().chunk_sizes(data, method) or [0]


class NegativeRemainder(Model):
    """Rolls with the `%` of most languages, which keeps the sign of a negative value."""

    def roll(self, value: int, out: int | None, new: int) -> int:
        if out is not None:
            value = truncated_remainder(value - out * self.power(), MODULUS)
        return truncated_remainder(value * BASE + new, MODULUS)

    def boundary(self, value: int) -> bool:
        return truncated_remainder(value, DIVISOR) == 0


class ThirtyTwoBitHash(Model):
    """Rolls in 32-bit integers, which overflow."""

    def roll(self, value: int, out: int | None, new: int) -> int:
        if out is not None:
            value = wrap32(value - wrap32(out * self.power()))
            value = (value % MODULUS + MODULUS) % MODULUS
        return wrap32(wrap32(value * BASE) + new) % MODULUS


class HashNeverForgets(Model):
    """Adds each byte but never removes the one that leaves the window."""

    def roll(self, value: int, out: int | None, new: int) -> int:
        return (value * BASE + new) % MODULUS


class WindowOfFifteen(Model):
    """Removes the leaving byte one position early, so the window holds 15 bytes."""

    def window_hashes(self, data: bytes) -> list[int]:
        hashes, value = [], 0
        for index, byte in enumerate(data):
            out = data[index - WINDOW + 1] if index >= WINDOW - 1 else None
            value = self.roll(value, out, byte)
            hashes.append(value)
        return hashes

    def power(self) -> int:
        return pow(BASE, WINDOW - 2, MODULUS)


class LeavingByteWeighsTooMuch(Model):
    """Removes the leaving byte with 257^16 instead of 257^15."""

    def power(self) -> int:
        return pow(BASE, WINDOW, MODULUS)


class NoMinimumSize(Model):
    """Cuts at any matching hash, however short the chunk."""

    def cut_here(self, length: int, value: int) -> bool:
        return length == MAX_CHUNK or (length >= WINDOW and self.boundary(value))


class MinimumOffByOne(Model):
    """Wants more than 32 bytes before a matching hash may cut."""

    def cut_here(self, length: int, value: int) -> bool:
        return length == MAX_CHUNK or (length > MIN_CHUNK and self.boundary(value))


class NoMaximumSize(Model):
    """Cuts only at a matching hash."""

    def cut_here(self, length: int, value: int) -> bool:
        return length >= MIN_CHUNK and self.boundary(value)


class MaximumOffByOne(Model):
    """Lets a chunk reach 257 bytes."""

    def cut_here(self, length: int, value: int) -> bool:
        return length == MAX_CHUNK + 1 or (length >= MIN_CHUNK and self.boundary(value))


class CutBeforeTheByte(Model):
    """Cuts before the position whose window matches, leaving that byte to the next chunk."""

    def cdc_sizes(self, data: bytes) -> list[int]:
        hashes = self.window_hashes(data)
        sizes, start = [], 0
        for index in range(len(data)):
            length = index - start + 1
            if length == MAX_CHUNK:
                sizes.append(length)
                start = index + 1
            elif length > MIN_CHUNK and self.boundary(hashes[index]):
                sizes.append(length - 1)
                start = index
        return [*sizes, len(data) - start] if start < len(data) else sizes


class ManifestWithSizes(Model):
    """Writes each chunk's size after its address in the manifest."""

    def manifest_line(self, address: str, chunk: bytes) -> str:
        return f"{address} {len(chunk)}\n"


class ChunksNotStored(Model):
    """Stores the manifest but keeps the chunks out of the store's objects."""

    def __init__(self) -> None:
        super().__init__()
        self.chunks: dict[str, bytes] = {}

    def put_file(self, data: str, method: str) -> str:
        raw, chunks, start = self.encode(data), [], 0
        for size in self.chunk_sizes(data, method):
            chunk = raw[start : start + size]
            self.chunks[self.address(chunk)] = chunk
            chunks.append((self.address(chunk), chunk))
            start += size
        self.remember(method, raw, chunks)
        return self.put("".join(self.manifest_line(address, chunk) for address, chunk in chunks))

    def read_chunk(self, address: str) -> bytes | None:
        return self.chunks.get(address)


class ReadFileUnchecked(Model):
    """Joins the chunks without checking them."""

    def read_chunk(self, address: str) -> bytes | None:
        return self.objects.get(address)


class ReadFileSkipsDamage(Model):
    """Leaves a damaged chunk out and returns the rest."""

    def read_chunk(self, address: str) -> bytes | None:
        return self.read(address) or b""


class RatioOfIntegers(Model):
    """Divides with integer division."""

    def ratio(self, logical: int, stored: int) -> float:
        return float(logical // stored) if stored else 0.0


class RatioCountsRepeatedChunks(Model):
    """Counts a chunk as often as it appears."""

    def remember(self, method: str, data: bytes, chunks: Sequence[tuple[str, bytes]]) -> None:
        self.logical[method] += len(data)
        for index, (address, chunk) in enumerate(chunks):
            self.distinct[method][f"{address}-{self.logical[method]}-{index}"] = len(chunk)


class RatioOverBothMethods(Model):
    """Keeps one total for both methods."""

    def dedup_ratio(self, method: str) -> float:
        logical = sum(self.logical.values())
        stored = {
            address: size for sizes in self.distinct.values() for address, size in sizes.items()
        }
        return self.ratio(logical, sum(stored.values()))


class RatioOverStoredObjects(Model):
    """Divides by every byte the store holds, manifests and other objects included."""

    def dedup_ratio(self, method: str) -> float:
        return self.ratio(self.logical[method], self.bytes_stored())


class RatioWithoutZeroGuard(Model):
    """Answers 1 when nothing has been chunked yet."""

    def ratio(self, logical: int, stored: int) -> float:
        return logical / stored if stored else 1.0


# ------------------------------------------------------------------ level 4 mistakes
class SetRefToNothing(Model):
    """Points a ref at an address that holds nothing."""

    def set_ref(self, name: str, kind: str, address: str) -> bool:
        if kind not in KINDS:
            return False
        self.refs[name] = (kind, address)
        return True


class SetRefAnyKind(Model):
    """Accepts any kind."""

    def set_ref(self, name: str, kind: str, address: str) -> bool:
        if address not in self.objects:
            return False
        self.refs[name] = (kind if kind in KINDS else "blob", address)
        return True


class SetRefNeedsAnIntactObject(Model):
    """Refuses a damaged object."""

    def set_ref(self, name: str, kind: str, address: str) -> bool:
        return self.intact(address) and super().set_ref(name, kind, address)


class SetRefKeepsTheFirst(Model):
    """Leaves a ref where it was when its name is set again."""

    def set_ref(self, name: str, kind: str, address: str) -> bool:
        if name in self.refs:
            return kind in KINDS and address in self.objects
        return super().set_ref(name, kind, address)


class DeleteRefAlwaysTrue(Model):
    """Answers true for a ref that does not exist."""

    def delete_ref(self, name: str) -> bool:
        self.refs.pop(name, None)
        return True


class DeleteRefFreesItsObjects(Model):
    """Deletes what the ref reached at once, shared objects included."""

    def delete_ref(self, name: str) -> bool:
        if name not in self.refs:
            return False
        kind, address = self.refs.pop(name)
        pending, seen = [(kind, address)], set()
        while pending:
            kind, address = pending.pop()
            if address in seen or address not in self.objects:
                continue
            seen.add(address)
            with contextlib.suppress(DamagedError):
                pending.extend(self.reached(kind, address))
            del self.objects[address]
        return True


class MarkOneLevelDeep(Model):
    """Marks a tree's lines but never opens its folders."""

    def reached(self, kind: str, address: str) -> list[Entry]:
        found = super().reached(kind, address)
        return [("blob", inner) for _, inner in found] if kind == "tree" else found


class ManifestsKeepNoChunks(Model):
    """Marks a manifest but not its chunks."""

    def reached(self, kind: str, address: str) -> list[Entry]:
        return [] if kind == "manifest" else super().reached(kind, address)


class BlobRefsOpened(Model):
    """Reads a blob's bytes as a folder when they look like one."""

    def reached(self, kind: str, address: str) -> list[Entry]:
        if kind == "blob" and address in self.objects:
            try:
                return list(self.parse(self.decode(self.objects[address])).values())
            except ValueError:
                return []
        return super().reached(kind, address)


class VisitedByAddress(Model):
    """Remembers visited addresses, not kinds, so a tree first reached as a blob is never opened."""

    def visit_key(self, kind: str, address: str) -> Entry | str:
        return address


class OnlyTheLastRef(Model):
    """Marks from the ref set most recently."""

    def roots(self) -> list[Entry]:
        return list(self.refs.values())[-1:]


class FreedObjectsCounted(Model):
    """Returns how many objects were freed instead of their bytes."""

    def sweep(self, live: set[str]) -> int:
        dead = [address for address in self.objects if address not in live]
        for address in dead:
            del self.objects[address]
        return len(dead)


class SweepsAfterAFailedMark(Model):
    """Skips a tree it cannot open and sweeps anyway."""

    def reached(self, kind: str, address: str) -> list[Entry]:
        try:
            return super().reached(kind, address)
        except DamagedError:
            return []


class StopsOnAnyDamage(Model):
    """Refuses to collect while any object is damaged, reachable or not."""

    def collect_garbage(self) -> int:
        if any(not self.intact(address) for address in self.objects):
            return -1
        return super().collect_garbage()


class OpensFilesToo(Model):
    """Checks every live object, files and chunks included, and stops on a damaged one."""

    def reached(self, kind: str, address: str) -> list[Entry]:
        if kind == "blob" and not self.intact(address):
            raise DamagedError(address)
        return super().reached(kind, address)


class SweepsBeforeAnsweringMinusOne(Model):
    """Answers -1 for a failed mark, but sweeps what the mark did reach anyway."""

    def __init__(self) -> None:
        super().__init__()
        self.failed = False

    def reached(self, kind: str, address: str) -> list[Entry]:
        try:
            return super().reached(kind, address)
        except DamagedError:
            self.failed = True
            return []

    def collect_garbage(self) -> int:
        self.failed = False
        freed = self.sweep(self.mark())
        return -1 if self.failed else freed


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def same(actual: list[Any], expected: list[Any]) -> bool:
    """The ops comparator: exact, except the ratio, which is compared as a float."""
    if len(actual) != len(expected):
        return False
    for got, want in zip(actual, expected, strict=True):
        if isinstance(want, float) and not isinstance(got, bool):
            if not isinstance(got, int | float) or not math.isclose(got, want, rel_tol=1e-6):
                return False
        elif got != want or type(got) is not type(want):
            return False
    return True


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return same(outputs(model_type, case), case["expected"])
    except (IndexError, KeyError, ValueError, TypeError, UnicodeDecodeError, DamagedError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert same(outputs(Model, case), case["expected"])


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_addresses_of_nists_examples_and_of_the_empty_message_are_checked():
    vectors = next(case for case in CASES if case["id"] == "h1")
    for message in (b"", b"abc", b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"):
        assert sha256_hex(message) in vectors["expected"]


def test_the_rust_reference_carries_the_starter_helper_unchanged():
    helper = RUST_HELPER.read_text(encoding="utf-8")
    assert helper in RUST_REFERENCE.read_text(encoding="utf-8")


@pytest.mark.slow
def test_the_rust_helper_passes_its_tests_against_known_digests(tmp_path: Path):
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc is not installed")
    binary = tmp_path / "sha256_tests"
    built = subprocess.run(
        [rustc, "--edition", "2021", "--test", str(RUST_HELPER), "-o", str(binary)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert built.returncode == 0, built.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "4 passed" in run.stdout
