"""Mutation testing in miniature: plant one small change at a time, and see which tests notice.

Each mutant is the function's syntax tree with one operator swapped, one constant changed or
one condition negated. A suite kills a mutant when one of its checks gives a different answer;
a mutant that no check notices survives.
"""

import ast
import copy

SOURCE = """
def shipping_cost(weight_kg, express):
    cost = 5
    if weight_kg > 2:
        cost += 3 * (weight_kg - 2)
    if express:
        cost *= 2
    return cost
"""

SWAPS = {ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Lt: ast.LtE, ast.LtE: ast.Lt,
         ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div}


def mutation_sites(tree: ast.AST) -> list[tuple[int, str]]:
    """Every place one change can go, as (index of the node in ast.walk order, kind)."""
    sites = []
    for index, node in enumerate(ast.walk(tree)):
        if isinstance(node, (ast.BinOp, ast.AugAssign)) and type(node.op) in SWAPS:
            sites.append((index, "operator"))
        elif isinstance(node, ast.Compare) and type(node.ops[0]) in SWAPS:
            sites.append((index, "comparison"))
        elif isinstance(node, ast.Constant) and isinstance(node.value, int):
            sites.append((index, "plus one"))
        elif isinstance(node, ast.If):
            sites.append((index, "negate"))
    return sites


def mutate(tree: ast.AST, index: int, kind: str) -> tuple[ast.AST, str]:
    """A copy of the tree with one change, and the first line of the statement it changed."""
    mutant = copy.deepcopy(tree)
    node = list(ast.walk(mutant))[index]
    if kind == "operator":
        node.op = SWAPS[type(node.op)]()
    elif kind == "comparison":
        node.ops = [SWAPS[type(node.ops[0])]()]
    elif kind == "plus one":
        node.value += 1
    else:
        node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
    return ast.fix_missing_locations(mutant), first_line(statement_of(node, mutant))


def statement_of(node: ast.AST, tree: ast.AST) -> ast.stmt:
    parents = {child: parent for parent in ast.walk(tree)
               for child in ast.iter_child_nodes(parent)}
    while not isinstance(node, ast.stmt):
        node = parents[node]
    return node


def first_line(statement: ast.stmt) -> str:
    return ast.unparse(statement).splitlines()[0]


def compile_function(tree: ast.AST):
    namespace = {}
    exec(compile(tree, "<mutant>", "exec"), namespace)
    return namespace["shipping_cost"]


SUITES = {
    "weak": [((3, True), 16)],
    "strong": [((3, True), 16), ((1, False), 5), ((4, False), 11)],
}

original = ast.parse(SOURCE)
nodes = list(ast.walk(original))
mutants = []
for index, kind in mutation_sites(original):
    mutant, changed = mutate(original, index, kind)
    mutants.append((mutant, first_line(statement_of(nodes[index], original)), changed))
survivors = {name: [] for name in SUITES}
for mutant, before, changed in mutants:
    function = compile_function(mutant)
    verdicts = []
    for name, checks in SUITES.items():
        try:
            killed = any(function(*args) != expected for args, expected in checks)
        except ArithmeticError:
            killed = True  # a crash is noticed too
        verdicts.append("killed" if killed else "survived")
        if not killed:
            survivors[name].append(changed)
    print(f"{before:<27} -> {changed:<28} weak {verdicts[0]:<8} "
          f"strong {verdicts[1]}")
for name in SUITES:
    print(f"{name}: killed {len(mutants) - len(survivors[name])} of {len(mutants)}")
