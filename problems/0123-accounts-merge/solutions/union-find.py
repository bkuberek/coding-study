from collections import defaultdict


def accounts_merge(accounts: list[list[str]]) -> list[list[str]]:
    parent = list(range(len(accounts)))
    size = [1] * len(accounts)  # size[r]: number of accounts in the tree rooted at r

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:  # path compression: point the whole path at the root
            parent[x], x = root, parent[x]
        return root

    def union(a: int, b: int) -> None:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            return
        if size[root_a] < size[root_b]:
            root_a, root_b = root_b, root_a
        parent[root_b] = root_a  # union by size: the smaller tree goes under the larger
        size[root_a] += size[root_b]

    first_owner: dict[str, int] = {}  # address -> first account that listed it
    for i, account in enumerate(accounts):
        for address in account[1:]:
            union(first_owner.setdefault(address, i), i)

    addresses_by_root: defaultdict[int, set[str]] = defaultdict(set)
    for i, account in enumerate(accounts):
        addresses_by_root[find(i)].update(account[1:])
    return [[accounts[root][0], *sorted(addresses)] for root, addresses in addresses_by_root.items()]
