from bisect import bisect_left


def suggested_products(products: list[str], search_word: str) -> list[list[str]]:
    ordered = sorted(products)
    suggestions: list[list[str]] = []
    start = 0
    for typed in range(1, len(search_word) + 1):
        prefix = search_word[:typed]
        # Products starting with `prefix` form one block; it begins at the first product >= prefix.
        # A longer prefix never begins its block earlier, so the search can start at `start`.
        start = bisect_left(ordered, prefix, start)
        suggestions.append([product for product in ordered[start : start + 3] if product.startswith(prefix)])
    return suggestions
