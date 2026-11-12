"""How many nodes fit under a given height, and how tall a binary tree with n nodes can be.

Heights count edges here: a tree of one node has height 0."""

print("perfect tree: height  leaves  nodes")
for height in range(5):
    leaves = 2**height
    nodes = 2 ** (height + 1) - 1
    print(f"{height:>19} {leaves:>7} {nodes:>6}")

for n in (1, 7, 8, 1_000, 1_000_000):
    shortest = n.bit_length() - 1  # floor(log2 n): every level full except the last
    tallest = n - 1  # one node per level: the tree is a path
    print(f"{n:>9} nodes: height at least {shortest:>2}, at most {tallest}")
