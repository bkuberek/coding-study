# Debug: Char Boundary: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| count-chars | optimal | O(n) | O(n) | default answer: `chars().count()` to measure, `chars().take()` to cut |

## Approach: count-chars (Count and cut by characters, not bytes)

### Intuition

A Rust `String` is UTF-8, and its API is in bytes: `len()` returns the number of bytes, and `&label[a..b]` slices at byte offsets. ASCII characters take one byte each, so for the English catalog bytes and characters coincide and the code is right. Other characters take more: `é`, `ß` and Cyrillic letters take 2 bytes, `★`, `…` and most CJK characters take 3.

The shipped code mixes the two units in two places:

1. **The length check.** `label.len() <= width` compares bytes with a width in characters. "Café" has 4 characters but 5 bytes, so it is treated as too long and clipped to "Caf…" although it fits.
2. **The cut.** `&label[..width - 1]` cuts at a byte offset. If that offset falls inside a multi-byte character, the slice would produce invalid UTF-8, which a `str` must never hold, so Rust panics: `byte index 3 is not a char boundary`. In Japanese nearly every offset is inside a character, which is why that store crashes on almost every page.

The fix measures and cuts in characters: `chars().count()` for the length, and `chars().take(width - 1)` for the prefix.

### Debugging approach

1. **Read the panic.** It names the byte index, the character it falls inside, and that character's byte range: index 3 is inside `è`, which occupies bytes 2 to 3. So the code slices at byte offsets, and `è` is two bytes.
2. **Compare the two lengths.** For "Café", `label.len()` is 5 and `label.chars().count()` is 4. The clipped names are the ones whose byte length exceeds the width while their character count does not.
3. **List every byte-based operation.** `len()` and the range index are both byte-based; the width is in characters. Both must change.
4. **Test both symptoms.** A name that fits in characters only (`h1`, `h10`, `h12`) checks the length; a name cut inside a multi-byte character (`h2`, `h5`) checks the slice.

### Algorithm

1. If `label` has at most `width` characters (`chars().count()`), return it unchanged.
2. Otherwise collect its first `width - 1` characters into a new `String` and push `'…'`.

### Correctness

`chars()` decodes UTF-8 into code points, so `chars().count()` is the length in the statement's unit, and the comparison returns the label unchanged exactly when it fits. Otherwise the label has more than `width` characters, so it has at least `width - 1`, and `take(width - 1)` yields exactly that many whole characters; a `String` collected from `char`s is valid UTF-8 by construction, so no cut can split a character. With the ellipsis the result has exactly `width` characters. `width >= 1`, so `width - 1` cannot underflow; for `width == 1` the result is the ellipsis alone.

### Complexity

- Time: O(n) — counting and taking each walk at most the n characters of the label once.
- Space: O(n) — the new, shorter string.

### Trade-offs

Collecting into a new `String` is the clearest fix. Slicing without copying the characters one by one is also possible: `label.char_indices().nth(width - 1)` gives the byte offset where character `width - 1` starts, and `&label[..offset]` is then guaranteed to be on a boundary. `str::is_char_boundary` checks a byte offset, and `floor_char_boundary` (Rust 1.91, newer than the 1.80 this catalog supports) rounds one down to a boundary, which suits limits measured in bytes (a database column, a protocol field) rather than in characters. For widths as people see them, neither bytes nor code points are right: combining accents, emoji sequences and double-width CJK characters need grapheme segmentation and display widths (the `unicode-segmentation` and `unicode-width` crates).

### Pitfalls and edge cases

- The general trap: `String::len`, `&s[a..b]`, `find` results and `split_at` are all in bytes. Mixing them with counts in characters works for ASCII and fails for everything else.
- `s.chars().nth(i)` is O(i), not O(1). Do not index characters in a loop with it; iterate once instead.
- `s.as_bytes()[i]` never panics on a boundary but yields raw bytes, and turning a cut byte slice back into a string needs `from_utf8`, which fails or replaces bytes (`from_utf8_lossy`).
- A label of exactly `width` characters but more bytes must stay unchanged (`h10`, `h12`).
- The ellipsis itself is one character but three bytes, so a label that already contains `…` (`h9`) breaks byte arithmetic too.

### Prevention

- Name units in variables and parameters: `width_chars`, `limit_bytes`.
- Test text handling with non-ASCII data from the start: accented Latin, Cyrillic, CJK and symbols such as `…` and `★`.
- Prefer iterator methods (`chars`, `char_indices`) over byte offsets for anything measured in characters.

### Language notes

- Rust only in this problem. Go strings are UTF-8 byte sequences too, and `len(s)` and `s[:n]` are byte-based, but Go does not panic: the slice silently produces invalid UTF-8, which shows up later as `�`. Java, Kotlin and TypeScript strings are UTF-16, so every character in this problem's constraints is one code unit and `substring` would be correct (characters outside the BMP would break them the same way). Python's `str` indexes code points, so `label[:width - 1]` is correct.
- Rust refuses `label[i]` entirely: a `String` cannot be indexed by an integer, because no single meaning (byte, code point or grapheme) is right for every use.
