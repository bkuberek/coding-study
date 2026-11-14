"""Answer a basic graph pattern the way SPARQL defines it: solutions of each pattern, then joins.

A solution is a dictionary from variables to terms. Each triple pattern, matched against the
graph, gives a list of solutions; two solutions are compatible when they agree on every variable
they share, and the join of two lists merges every compatible pair. Joining in another order
gives the same answers, through intermediate lists of other sizes.
"""

GRAPH = {
    (":ada", ":worksFor", ":bakery"), (":bob", ":worksFor", ":bakery"),
    (":cy", ":worksFor", ":library"), (":dee", ":worksFor", ":clinic"),
    (":bakery", ":basedIn", ":paris"), (":library", ":basedIn", ":oslo"),
    (":clinic", ":basedIn", ":paris"), (":ada", ":knows", ":cy"),
    (":ada", ":knows", ":dee"), (":cy", ":knows", ":cy"),
}


def match(pattern: tuple[str, str, str]) -> list[dict[str, str]]:
    solutions = []
    for triple in sorted(GRAPH):
        solution: dict[str, str] = {}
        for slot, term in zip(pattern, triple):
            if slot.startswith("?"):
                if solution.setdefault(slot, term) != term:  # ?x twice must be one term
                    break
            elif slot != term:
                break
        else:
            solutions.append(solution)
    return solutions


def join(left: list[dict], right: list[dict]) -> list[dict]:
    return [{**a, **b} for a in left for b in right
            if all(a[v] == b[v] for v in a.keys() & b.keys())]


def evaluate(bgp: list[tuple[str, str, str]], show: bool = False) -> list[dict]:
    solutions: list[dict] = [{}]  # the join of no patterns: one solution that binds nothing
    for pattern in bgp:
        solutions = join(solutions, match(pattern))
        if show:
            print(f"  after {' '.join(pattern)}: {len(solutions)} solutions")
    return solutions


def select_distinct(solutions: list[dict], *variables: str) -> list[tuple[str, ...]]:
    return sorted({tuple(s[v] for v in variables) for s in solutions})


query = [(":ada", ":knows", "?friend"), ("?friend", ":worksFor", "?org"),
         ("?org", ":basedIn", "?city")]
for order in (query, query[::-1]):
    print("order:", " . ".join(" ".join(p) for p in order))
    answer = evaluate(order, show=True)
print("SELECT DISTINCT ?city:", select_distinct(answer, "?city"))
print("works for an org based in :paris:", select_distinct(
    evaluate([("?who", ":worksFor", "?org"), ("?org", ":basedIn", ":paris")]), "?who"))
print("knows themselves:", select_distinct(evaluate([("?x", ":knows", "?x")]), "?x"))
