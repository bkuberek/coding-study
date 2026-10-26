ON_PATH = "on path"


def find_all_recipes(
    recipes: list[str], ingredients: list[list[str]], supplies: list[str]
) -> list[str]:
    needs = dict(zip(recipes, ingredients))
    stocked = set(supplies)
    # Memo per recipe: True or False once decided, ON_PATH while it is being explored.
    verdict: dict[str, bool | str] = {}

    def can_prepare(item: str) -> bool:
        if item in stocked:
            return True
        if item not in needs:
            return False  # neither a supply nor a recipe
        known = verdict.get(item)
        if known == ON_PATH:
            return False  # the ingredients loop back to this recipe
        if known is not None:
            return bool(known)
        verdict[item] = ON_PATH
        result = all(can_prepare(ingredient) for ingredient in needs[item])
        verdict[item] = result
        return result

    return [recipe for recipe in recipes if can_prepare(recipe)]
