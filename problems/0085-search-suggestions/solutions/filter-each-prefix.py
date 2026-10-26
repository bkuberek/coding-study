def suggested_products(products: list[str], search_word: str) -> list[list[str]]:
    suggestions: list[list[str]] = []
    for typed in range(1, len(search_word) + 1):
        prefix = search_word[:typed]
        matches = sorted(product for product in products if product.startswith(prefix))
        suggestions.append(matches[:3])
    return suggestions
