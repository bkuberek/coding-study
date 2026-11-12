"""A table of command names stored in a trie: exact lookup, counts by prefix, the shortest
abbreviation of each command that no other command shares, and what an abbreviation means.

Every node counts the commands whose name passes through it, so the number of commands that start
with a prefix is read at the prefix's last node, without visiting the commands below it.
"""

COMMANDS = {
    "branch": "list or create branches",
    "build": "compile the project",
    "bump": "raise the version number",
    "check": "run the linters",
    "clean": "delete build output",
    "clone": "copy a repository",
    "commit": "record changes",
    "log": "show the history",
    "login": "store credentials",
    "logout": "forget credentials",
}


class Node:
    def __init__(self) -> None:
        self.children: dict[str, Node] = {}
        self.passing = 0  # how many stored names go through this node
        self.help: str | None = None  # set when a stored name ends exactly here


class CommandTrie:
    def __init__(self) -> None:
        self.root = Node()

    def walk(self, prefix: str) -> Node | None:
        node = self.root
        for letter in prefix:
            node = node.children.get(letter)
            if node is None:
                return None
        return node

    def insert(self, name: str, summary: str) -> None:
        existing = self.walk(name)
        if existing is not None and existing.help is not None:
            existing.help = summary  # already stored: replace its help, but count it only once
            return
        node = self.root
        node.passing += 1
        for letter in name:
            node = node.children.setdefault(letter, Node())
            node.passing += 1
        node.help = summary

    def lookup(self, name: str) -> str | None:
        node = self.walk(name)
        return None if node is None else node.help

    def count_starting_with(self, prefix: str) -> int:
        node = self.walk(prefix)
        return 0 if node is None else node.passing

    def shortest_unique_prefix(self, name: str) -> str:
        node = self.root
        for length, letter in enumerate(name, start=1):
            node = node.children[letter]
            if node.passing == 1:
                return name[:length]
        return name  # another name starts with this whole name: only typing all of it is unique

    def resolve(self, typed: str) -> str:
        node = self.walk(typed)
        if node is None:
            return "unknown"
        if node.help is not None:
            return typed  # a complete name wins, even when longer names start with it
        if node.passing > 1:
            return f"ambiguous, {node.passing} commands"
        while node.help is None:  # one name passes here: follow its only path to the end
            ((letter, node),) = node.children.items()
            typed += letter
        return typed


def count_nodes(node: Node) -> int:
    return sum(1 + count_nodes(child) for child in node.children.values())


table = CommandTrie()
for name, summary in COMMANDS.items():
    table.insert(name, summary)

print("lookup('clone'):", table.lookup("clone"))
print("lookup('clo'):  ", table.lookup("clo"), "(a prefix, not a command)")
for prefix in ("c", "cl", "lo", "b", "x"):
    print(f"commands starting with {prefix!r}: {table.count_starting_with(prefix)}")
print("shortest unique prefixes:", ", ".join(table.shortest_unique_prefix(n) for n in COMMANDS))
for typed in ("br", "bu", "co", "log", "logi", "logo", "z"):
    print(f"{typed!r} means: {table.resolve(typed)}")
letters = sum(len(name) for name in COMMANDS)
print(f"{len(COMMANDS)} names, {letters} letters, {count_nodes(table.root)} nodes below the root")
