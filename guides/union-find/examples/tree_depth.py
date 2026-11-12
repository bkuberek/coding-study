"""How deep the trees get with and without union by size and path compression, for 1,024 elements.

Two orders of unions are tried: a chain (0 with 1, then 1 with 2, ...) and a tournament (pairs,
then pairs of pairs, ...), which is the worst order for union by size."""

N = 1024


class Forest:
    def __init__(self, by_size: bool) -> None:
        self.parent = list(range(N))
        self.size = [1] * N
        self.by_size = by_size

    def find(self, x: int, compress: bool = False) -> int:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while compress and self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a == root_b:
            return
        if self.by_size and self.size[root_a] < self.size[root_b]:
            root_a, root_b = root_b, root_a
        self.parent[root_b] = root_a  # plain linking always hangs b's tree under a's root
        self.size[root_a] += self.size[root_b]

    def depths(self) -> list[int]:
        result = []
        for x in range(N):
            steps = 0
            while self.parent[x] != x:
                x, steps = self.parent[x], steps + 1
            result.append(steps)
        return result


chain = [(i + 1, i) for i in range(N - 1)]
tournament = []
width = 1
while width < N:
    tournament += [(start, start + width) for start in range(0, N, 2 * width)]
    width *= 2

for name, unions in [("chain", chain), ("tournament", tournament)]:
    for by_size in (False, True):
        forest = Forest(by_size)
        for a, b in unions:
            forest.union(a, b)
        depth = forest.depths()
        rule = "union by size" if by_size else "plain linking"
        print(f"{name:>10}, {rule}: deepest {max(depth):>4}, sum of depths {sum(depth):>6}")

forest = Forest(by_size=True)
for a, b in tournament:
    forest.union(a, b)
for x in range(N):
    forest.find(x, compress=True)
depth = forest.depths()
print(f"tournament, union by size, then one compressing find of each: deepest {max(depth)}")
