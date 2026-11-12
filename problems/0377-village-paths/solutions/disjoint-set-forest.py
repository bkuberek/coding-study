class VillageMap:
    def __init__(self, villages: int) -> None:
        self.parent = list(range(villages))  # parent[v] == v marks the leader of a group
        self.size = [1] * villages  # size[r]: villages in the group whose leader is r
        self.groups = villages

    def _leader(self, village: int) -> int:
        leader = village
        while self.parent[leader] != leader:
            leader = self.parent[leader]
        # Path compression: send everything passed on the way straight to the leader.
        while self.parent[village] != leader:
            self.parent[village], village = leader, self.parent[village]
        return leader

    def add_path(self, a: int, b: int) -> bool:
        leader_a, leader_b = self._leader(a), self._leader(b)
        if leader_a == leader_b:
            return False
        if self.size[leader_a] < self.size[leader_b]:
            leader_a, leader_b = leader_b, leader_a
        self.parent[leader_b] = leader_a  # union by size: the smaller group joins the larger
        self.size[leader_a] += self.size[leader_b]
        self.groups -= 1
        return True

    def can_reach(self, a: int, b: int) -> bool:
        return self._leader(a) == self._leader(b)

    def group_size(self, village: int) -> int:
        return self.size[self._leader(village)]

    def group_count(self) -> int:
        return self.groups
