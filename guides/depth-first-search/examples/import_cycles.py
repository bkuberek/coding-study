"""Three colors tell a module imported twice from a circular import.

white: not reached yet. gray: entered and not finished, so it is on the current path.
black: finished, with everything it imports. An edge to a gray module closes a cycle."""

WHITE, GRAY, BLACK = "white", "gray", "black"


def find_cycle(imports: dict[str, list[str]]) -> list[str] | None:
    color = dict.fromkeys(imports, WHITE)
    path: list[str] = []

    def visit(module: str) -> list[str] | None:
        color[module] = GRAY
        path.append(module)
        print(f"  enter {module}")
        for imported in imports[module]:
            if color[imported] == GRAY:
                print(f"  {module} imports {imported}, which is gray: a cycle")
                return [*path[path.index(imported) :], imported]
            if color[imported] == BLACK:
                print(f"  {module} imports {imported}, which is black: already finished")
                continue
            cycle = visit(imported)
            if cycle:
                return cycle
        color[module] = BLACK
        path.pop()
        print(f"  leave {module}")
        return None

    for module in imports:
        if color[module] == WHITE:
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
