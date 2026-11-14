"""The same three-table join in every left-deep order, and how many rows each order produces.

The query: the sales of the stores in the region named "north".
  regions: 4 rows (id, name); stores: 40 rows (id, region); sales: 4,000 rows (id, store).
  sales.store = stores.id AND stores.region = regions.id AND regions.name = 'north'
Each order starts from one table, with its filter applied, and joins one table at a time, using
only tables that share a join condition with what is already joined (no Cartesian product). The
estimate follows the 1979 System R rules: a filter keeps 1 / (distinct values) of the rows, and a
join keeps 1 / (the larger number of distinct values of its two columns) of the pairs.
"""

from itertools import permutations

NAMES = ["north", "south", "east", "west"]


def tables(skewed: bool) -> dict[str, list[dict]]:
    regions = [{"id": r, "name": NAMES[r]} for r in range(4)]
    stores = [{"id": s, "region": s % 4} for s in range(40)]
    north = [s for s in range(40) if s % 4 == 0]
    others = [s for s in range(40) if s % 4 != 0]
    if skewed:  # 7 sales in 10 go to the 10 northern stores
        sales = [
            {"store": north[(k // 10) % 10] if k % 10 < 7 else others[(k // 10) % 30]}
            for k in range(4000)
        ]
    else:
        sales = [{"store": k % 40} for k in range(4000)]
    return {"regions": regions, "stores": stores, "sales": sales}


JOINS = {
    frozenset({"sales", "stores"}): ("sales", "store", "stores", "id"),
    frozenset({"stores", "regions"}): ("stores", "region", "regions", "id"),
}


def keep(table: str, row: dict) -> bool:
    return table != "regions" or row["name"] == "north"


def run(order: tuple[str, ...], data: dict) -> list[int] | None:
    rows = [{order[0]: r} for r in data[order[0]] if keep(order[0], r)]
    sizes = []
    for i, table in enumerate(order[1:], start=1):
        links = [JOINS[frozenset({table, t})] for t in order[:i] if frozenset({table, t}) in JOINS]
        if not links:
            return None  # would be a Cartesian product
        a, ca, b, cb = links[0]
        index: dict[int, list[dict]] = {}
        for r in data[table]:
            if keep(table, r):
                index.setdefault(r[ca] if table == a else r[cb], []).append(r)
        rows = [
            {**row, table: r}
            for row in rows
            for r in index.get(row[b][cb] if table == a else row[a][ca], [])
        ]
        sizes.append(len(rows))
    return sizes


for skewed in (False, True):
    data = tables(skewed)
    print("skewed data: 70% of the sales are northern" if skewed else "uniform data")
    for order in permutations(["regions", "stores", "sales"]):
        sizes = run(order, data)
        if sizes is None:
            print(f"  {' > '.join(order):<26} skipped: needs a Cartesian product")
        else:
            print(f"  {' > '.join(order):<26} rows after each join {sizes}, total {sum(sizes):,}")
    north = 4 // 4  # 4 regions, 4 distinct names
    with_stores = 40 * north // max(4, 4)  # stores.region and regions.id: 4 distinct each
    estimate = 4000 * with_stores // max(40, 40)  # sales.store and stores.id: 40 distinct each
    print(f"  estimated: {north} region, {with_stores} stores, {estimate:,} sales")
