"""A package manager installs what a package needs before the package itself, each one once."""

# Made-up packages and what each one needs.
NEEDS = {
    "editor": ["spellcheck", "syntax"],
    "spellcheck": ["dictionary", "unicode"],
    "syntax": ["unicode"],
    "dictionary": [],
    "unicode": [],
}


def install_order(package: str, installed: set[str]) -> list[str]:
    """Every package to install for `package`, dependencies first, skipping what is installed."""
    order: list[str] = []

    def visit(name: str) -> None:
        if name in installed or name in order:
            return
        for dependency in NEEDS[name]:
            visit(dependency)
        order.append(name)

    visit(package)
    return order


print("install editor on an empty machine:", install_order("editor", set()))
print("install editor when unicode is there:", install_order("editor", {"unicode"}))
print("install syntax alone:", install_order("syntax", set()))


def broken_by_removing(package: str) -> list[str]:
    """Every other package that needs `package`, directly or through another package."""
    return [name for name in NEEDS if name != package and package in install_order(name, set())]


print("removing unicode would break:", broken_by_removing("unicode"))
print("removing editor would break:", broken_by_removing("editor"))
