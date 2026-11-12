class VillageMap:
    def __init__(self, villages: int) -> None:
        self.label = list(range(villages))  # label[v]: the name of the group of village v
        self.members = [1] * villages  # members[g]: how many villages carry label g
        self.groups = villages

    def add_path(self, a: int, b: int) -> bool:
        keep, drop = self.label[a], self.label[b]
        if keep == drop:
            return False
        # Every village of the dropped group has to learn its new label.
        for village, label in enumerate(self.label):
            if label == drop:
                self.label[village] = keep
        self.members[keep] += self.members[drop]
        self.groups -= 1
        return True

    def can_reach(self, a: int, b: int) -> bool:
        return self.label[a] == self.label[b]

    def group_size(self, village: int) -> int:
        return self.members[self.label[village]]

    def group_count(self) -> int:
        return self.groups
