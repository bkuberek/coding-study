# Group Anagrams: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| linear-search | brute | O(n^2 k) | O(n k) | very few words, or as a correctness oracle |
| sorted-key | optimal | O(n k log k) | O(n k) | default answer; short words or any alphabet |
| count-key | optimal | O(n k) | O(n k) | long words over a small fixed alphabet |

Here n is the number of words and k the maximum word length. Every approach relies on one idea: anagrams share a canonical key, and words with equal keys form a group. The approaches differ in how the key is built and how the group with a given key is found.

## Approach: linear-search (Sorted keys with a linear search over groups)

### Intuition

Sorting the letters of a word gives a key that is identical for all of its anagrams and different for every other word. Keep the groups in a list next to their keys; for each word, look for its key among the groups found so far and either join that group or start a new one.

### Algorithm

1. Keep two parallel lists: `keys` and `groups`.
2. For each word:
   1. Compute `key`, the word's letters in sorted order.
   2. Search `keys` from the front for `key`.
   3. If found at position `i`, append the word to `groups[i]`; otherwise append `key` to `keys` and a new group `[word]` to `groups`.
3. Return `groups`.

### Correctness

Two words are anagrams exactly when their sorted forms are equal: sorting preserves letter counts, and a sorted string is determined by its letter counts. Invariant: `keys[i]` is the sorted form of every word in `groups[i]`, and the keys are pairwise distinct. A word joins the group with an equal key, or starts a new group when no key matches, so both properties are preserved. At the end, each word is in exactly one group, and two words share a group exactly when their keys are equal, that is, when they are anagrams.

### Complexity

- Time: O(n^2 k) — up to n groups, so each of the n searches can compare up to n keys of length up to k; sorting each word adds O(n k log k). With about n/2 groups in the generated inputs, the searches compare on the order of n^2/8 keys.
- Space: O(n k) — the keys and the output hold every letter a constant number of times.

### Trade-offs

It already uses the canonical key, so it shows exactly what the hash map adds: finding a key in O(k) instead of comparing it with every other key. At n = 10,000 it makes about 10^7 key comparisons, against about 10^4 hash lookups for the optimal approaches. Its only advantages are that it needs no hashing and that it returns groups in order of first appearance.

### Pitfalls and edge cases

- Comparing a word directly with the first word of each group (instead of with a key) needs an anagram check per comparison, which costs O(k) and repeats the work for every group.
- The empty word has the empty key; it must not be skipped.

### Language notes

- Python: `keys.index(key)` runs the comparisons in C and raises `ValueError` when the key is absent.
- TypeScript: `keys.indexOf(key)` compares strings by value with `===`.
- Java: `List.indexOf` uses `equals`, which compares string contents; `==` would compare references.
- Kotlin: `indexOf` uses structural equality (`==`), so string contents are compared.

## Approach: sorted-key (Hash map keyed by the sorted word)

### Intuition

Use the sorted word as a hash-map key. The map takes the group lookup from a linear search down to one hash and one equality check, so a single pass groups every word.

### Algorithm

1. Create an empty map from key to list of words.
2. For each word, compute its sorted form `key` and append the word to `map[key]`, creating the list when the key is new.
3. Return the map's values.

### Correctness

As in the linear search, two words are anagrams exactly when their sorted forms are equal. The map holds one list per distinct key and appends each word to the list for its own key, so the lists are exactly the classes of words with equal keys.

### Complexity

- Time: O(n k log k) — sorting each word costs O(k log k); hashing and comparing a key costs O(k).
- Space: O(n k) — the keys and the grouped words.

### Trade-offs

Short, idiomatic in every language and alphabet-independent, which makes it the default interview answer. For long words over a small alphabet, the O(k log k) sort per word loses to counting; for the short words of typical inputs the difference is small and sorting is often faster in practice because it is a tight built-in.

### Pitfalls and edge cases

- The key must be a value type with content equality: a Python `list`, a Java `char[]` or a Kotlin `CharArray` cannot be used as a key. Convert to a string first.
- Repeated words must stay repeated in the output: append, never deduplicate.

### Language notes

- Python: `"".join(sorted(word))` builds the key; `collections.defaultdict(list)` creates missing groups.
- TypeScript: `[...word].sort().join("")`; a `Map<string, string[]>` compares string keys by value. Return `[...groups.values()]`, because `values()` is an iterator, not an array.
- Java: sort the `char[]` from `toCharArray()` and wrap it in `new String(...)`; `computeIfAbsent` creates the group on first use. `new ArrayList<>(groups.values())` copies the view into a list.
- Kotlin: `strs.groupBy { ... }` builds a `LinkedHashMap` from key to list in one call; `.values.toList()` returns the groups.

## Approach: count-key (Hash map keyed by letter counts)

### Intuition

Anagrams are defined by their letter counts, so the 26 counts are themselves a canonical key. Counting a word takes O(k) instead of the O(k log k) sort.

### Algorithm

1. Create an empty map from key to list of words.
2. For each word:
   1. Count its letters into an array of 26 integers.
   2. Turn the counts into a hashable value with content equality (a tuple, a string or a list).
   3. Append the word to the group for that key.
3. Return the map's values.

### Correctness

Two words are anagrams exactly when every letter occurs equally often in both, which is exactly when their 26-entry count arrays are equal. The map groups words by that key, so each group holds one anagram class.

### Complexity

- Time: O(n k) — counting is O(k) per word; building, hashing and comparing a 26-entry key is O(1) per word for the fixed alphabet.
- Space: O(n k) — the grouped words, plus one 26-entry key per group.

### Trade-offs

Asymptotically the best for a fixed alphabet. Each key costs 26 entries even for a one-letter word, and the key conversion (a tuple, `Arrays.toString`, a `List<Int>`) has a noticeable constant cost, so on short words it is often no faster than sorting. It does not extend to an unbounded alphabet without switching the counts to a map.

### Pitfalls and edge cases

- The key must not be ambiguous. Concatenating counts without a separator collides: counts `[1, 11]` and `[11, 1]` both become `"111"`. The references use separators (`counts.join(",")`, `Arrays.toString`) or structured keys (tuple, list).
- Raw arrays compare by reference in Java, Kotlin and TypeScript: two equal count arrays are different keys unless converted.

### Language notes

- Python: `tuple(counts)` is hashable and compares by content.
- TypeScript: `counts.join(",")` produces a separated string key; `Map` would treat two equal arrays as different keys.
- Java: `Arrays.toString(counts)` gives `"[1, 0, ...]"`, an unambiguous string key. A `List<Integer>` key also works but boxes 26 values per word.
- Kotlin: `counts.toList()` returns a `List<Int>`, whose `equals` and `hashCode` are structural, so it works directly as a `HashMap` key; `getOrPut` creates missing groups.
