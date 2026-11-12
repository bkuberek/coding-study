"""Three colours tell a module imported twice from a circular import.

white: not reached yet. grey: entered and not finished, so it is on the current path.
black: finished, with everything it imports. An edge to a grey module closes a cycle."""

WHITE, GREY, BLACK = "white", "grey", "black"


def find_cycle(imports: dict[str, list[str]]) -> list[str] | None:
    colour = dict.fromkeys(imports, WHITE)
    path: list[str] = []

    def visit(module: str) -> list[str] | None:
        colour[module] = GREY
        path.append(module)
        print(f"  enter {module}")
        for imported in imports[module]:
            if colour[imported] == GREY:
                print(f"  {module} imports {imported}, which is grey: a cycle")
                return [*path[path.index(imported) :], imported]
            if colour[imported] == BLACK:
                print(f"  {module} imports {imported}, which is black: already finished")
                continue
            cycle = visit(imported)
            if cycle:
                return cycle
        colour[module] = BLACK
        path.pop()
        print(f"  leave {module}")
        return None

    for module in imports:
        if colour[module] == WHITE:
            cycle = visit(module)
            if cycle:
                return cycle
    return None


imports = {
    "app": ["auth", "ui"],
    "auth": ["db"],
    "db": ["config"],
    "config": [],
    "ui": ["auth", "theme"],
    "theme": [],
}
print("first project:")
print("cycle:", find_cycle(imports))

imports["config"] = ["db"]  # config now imports db, which imports config
print("second project:")
print("cycle:", find_cycle(imports))
