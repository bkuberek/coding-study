"""A registry of active sessions: add and remove by id in O(1), and keep every member in a dense
array, so it can be walked without gaps or reached by position.

Removing from the middle of an array costs O(n) because the tail shifts left. When order does
not matter, move the last member into the hole instead, and fix that one member's index.
"""


class DenseRegistry:
    def __init__(self) -> None:
        self.members: list[str] = []
        self.index: dict[str, int] = {}  # member -> its position in `members`

    def add(self, member: str) -> bool:
        if member in self.index:
            return False
        self.index[member] = len(self.members)
        self.members.append(member)
        return True

    def remove(self, member: str) -> bool:
        position = self.index.pop(member, None)
        if position is None:
            return False
        last = self.members.pop()
        if last != member:  # fill the hole with the last member
            self.members[position] = last
            self.index[last] = position
        return True


sessions = DenseRegistry()
for session in ("s1", "s2", "s3", "s4"):
    sessions.add(session)
print("members:", sessions.members, "index:", sessions.index)
sessions.remove("s2")
print("remove s2:", sessions.members, "index:", sessions.index)
sessions.remove("s4")
print("remove s4:", sessions.members, "index:", sessions.index)
print("add s1 again:", sessions.add("s1"), "| remove s9:", sessions.remove("s9"))
print("position 1 holds", sessions.members[1], "| any position from 0 to", len(sessions.members) - 1)
