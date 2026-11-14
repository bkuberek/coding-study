def find_all_recipes(
    recipes: list[str], ingredients: list[list[str]], supplies: list[str]
) -> list[str]:
    available = set(supplies)
    prepared: list[str] = []
    pending = list(range(len(recipes)))
    changed = True
    while changed:
        changed = False
        still_pending: list[int] = []
        for i in pending:
            if all(item in available for item in ingredients[i]):
                available.add(recipes[i])
                prepared.append(recipes[i])
                changed = True
            else:
                still_pending.append(i)
        pending = still_pending
    return prepared
