def replace_words(dictionary: list[str], sentence: str) -> str:
    shortened = []
    for word in sentence.split(" "):
        best = word
        for root in dictionary:
            if len(root) < len(best) and word.startswith(root):
                best = root
        shortened.append(best)
    return " ".join(shortened)
