def group_anagrams(strs: list[str]) -> list[list[str]]:
    keys: list[str] = []
    groups: list[list[str]] = []
    for word in strs:
        key = "".join(sorted(word))
        try:
            # list.index compares the key with every earlier group key, in C.
            groups[keys.index(key)].append(word)
        except ValueError:
            keys.append(key)
            groups.append([word])
    return groups
