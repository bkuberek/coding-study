from collections import defaultdict, deque


def find_all_recipes(
    recipes: list[str], ingredients: list[list[str]], supplies: list[str]
) -> list[str]:
    used_by: defaultdict[str, list[int]] = defaultdict(list)
    for i, items in enumerate(ingredients):
        for item in items:
            used_by[item].append(i)
    missing = [len(items) for items in ingredients]  # ingredients each recipe still lacks
    available = deque(supplies)
    prepared: list[str] = []
    while available:
        item = available.popleft()
        for i in used_by[item]:
            missing[i] -= 1
            if missing[i] == 0:
                prepared.append(recipes[i])
                available.append(recipes[i])
    return prepared
