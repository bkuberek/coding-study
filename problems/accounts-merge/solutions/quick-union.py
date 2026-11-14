from collections import defaultdict


def accounts_merge(accounts: list[list[str]]) -> list[list[str]]:
    parent = list(range(len(accounts)))  # parent[x] == x marks a root

    def find(x: int) -> int:
        while parent[x] != x:
            x = parent[x]
        return x

    first_owner: dict[str, int] = {}  # address -> first account that listed it
    for i, account in enumerate(accounts):
        for address in account[1:]:
            root_owner, root_here = find(first_owner.setdefault(address, i)), find(i)
            if root_owner != root_here:
                parent[root_owner] = root_here  # no balancing: trees can grow into long chains

    addresses_by_root: defaultdict[int, set[str]] = defaultdict(set)
    for i, account in enumerate(accounts):
        addresses_by_root[find(i)].update(account[1:])
    return [[accounts[root][0], *sorted(addresses)] for root, addresses in addresses_by_root.items()]
