# Encode and Decode Strings: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| length-prefix | optimal | O(n + L) | O(n + L) | default answer; decoding never inspects string contents |
| escaping | optimal | O(n + L) | O(n + L) | the encoding must stay human-readable or be streamed character by character |

Here n is the number of strings and L the total number of characters. Both formats are linear; no slower approach teaches anything here, because the difficulty is correctness, not speed. The naive format, joining with a delimiter, is not an approach but the bug both formats fix: `["a,b"]` and `["a", "b"]` both join to `"a,b"`.

The tests can only observe `decode(encode(strs))`, so they check the round trip. The statement still requires real `encode` and `decode` helpers that communicate only through the encoded string.

## Approach: length-prefix (Length-prefixed chunks)

### Intuition

A delimiter is ambiguous because it can also occur inside a string. A length is not: if `decode` knows that the next string has 5 characters, it copies 5 characters without looking at them, whatever they are. Writing each string as `<length>#<string>` works because the length contains only digits, so the first `#` after the current position always ends the length.

### Algorithm

1. `encode`: for each string `s`, append `len(s)`, then `#`, then `s`.
2. `decode`, starting at position 0 and repeating until the end of the encoded string:
   1. Find the first `#` at or after the current position.
   2. Parse the digits between the current position and that `#` as `length`.
   3. Take the `length` characters after the `#` as the next string.
   4. Move the position to just after that string.
3. `encodeDecode(strs)` returns `decode(encode(strs))`.

### Correctness

By induction over the strings: when `decode` starts reading the `i`-th chunk, its position is exactly where `encode` wrote the length of `strs[i]`. The chunk begins with that length's decimal digits; digits are never `#`, so the first `#` found is the one `encode` wrote after the length, and the parsed number is `len(strs[i])`. The next `len(strs[i])` characters are exactly `strs[i]`, even if they contain digits or `#`, because they are copied, not scanned. The position then lands on the start of chunk `i + 1`. The encoded string ends exactly after the last chunk, so `decode` returns exactly `n` strings; an empty list encodes to `""` and decodes to `[]`, while `[""]` encodes to `"0#"`.

### Complexity

- Time: O(n + L) — `encode` writes each character once plus a short prefix per string; `decode` scans each prefix once and copies each string's characters once.
- Space: O(n + L) — the encoded string and the decoded list.

### Trade-offs

Robust for any alphabet, because the content is never interpreted, and slightly faster than escaping since `decode` jumps over each string with a single slice. The encoding is less readable and cannot be decoded from the middle without knowing where a chunk starts. A fixed-width binary length (for example, 4 bytes) avoids the `#` marker entirely and is what real network protocols use.

### Pitfalls and edge cases

- Searching for `#` from the start of the whole string, instead of from the current position, finds a `#` inside an earlier string.
- Parsing only one digit of the length breaks strings of 10 or more characters.
- Lengths must count the same units in `encode` and `decode`. Java, Kotlin and TypeScript count UTF-16 code units and Python counts code points; this is consistent within one language, and every character here is ASCII anyway.

### Language notes

- Python: `encoded.index("#", position)` finds the marker in C; slicing copies the string.
- TypeScript: a template literal builds each chunk, `indexOf` finds the marker and `slice` extracts the string.
- Java: `StringBuilder` builds the encoding; `Integer.parseInt(encoded, position, marker, 10)` parses the digits in place without creating a substring (Java 9+).
- Kotlin: `buildString { ... }` wraps a `StringBuilder`; `substring(...).toInt()` parses the length.
- Go: `strings.Builder` appends without quadratic copying, `strconv.Itoa` and `strconv.Atoi` convert the length, and `strings.IndexByte` finds the marker. `len` counts bytes, which equals characters for the ASCII input, and slicing a string by byte offsets copies nothing.
- Rust: `String` is UTF-8, so `len()` is a byte count and `&encoded[start..end]` slices by byte offsets; both match the character count only because every character is ASCII, and a slice that split a multi-byte character would panic. `find` returns the marker's byte offset and `parse::<usize>()` reads the digits.

## Approach: escaping (Escaped terminators)

### Intuition

Keep a separator, but make it unambiguous: end every string with a terminator `,`, and inside a string write every `,` as `\,` and every `\` as `\\`. While decoding, a `\` always means "the next character is literal", so an unescaped `,` can only be a terminator.

### Algorithm

1. `encode`: for each string, emit every character, preceded by `\` when the character is `\` or `,`; then emit `,`.
2. `decode`: scan the characters with a flag `escaped`:
   1. If `escaped`, append the character to the current string and clear the flag.
   2. Else if the character is `\`, set the flag.
   3. Else if it is `,`, finish the current string and start a new, empty one.
   4. Else append it to the current string.
3. `encodeDecode(strs)` returns `decode(encode(strs))`.

### Correctness

In the encoding, every `\` written by `encode` is an escape immediately followed by the character it protects, and every unescaped `,` is a terminator. `decode` reads the encoding left to right in exactly those units: after a `\` it takes the next character literally, which undoes one escape; an unescaped `,` ends a string, which matches one terminator. So the `i`-th finished string is exactly the unescaped characters `encode` wrote for `strs[i]`, which is `strs[i]` itself. Because every string, even an empty one, ends with a terminator, the number of strings is preserved: `[]` encodes to `""` and `[""]` to `","`.

### Complexity

- Time: O(n + L) — each character is written at most twice and read once, plus one terminator per string.
- Space: O(n + L) — the encoding is at most twice the input plus one character per string.

### Trade-offs

The encoding stays readable and can be decoded as a stream, one character at a time, which suits incremental input. It inspects every character, so it is a little slower than jumping with a length, and the encoding can double in size when the input is full of `,` and `\`.

### Pitfalls and edge cases

- Escape order matters when using `replace`: escape `\` first, then `,`. In the other order, the backslashes added for commas get doubled.
- Using `,` as a separator between strings (join) instead of a terminator after each string makes `[]` and `[""]` both encode to `""`.
- Choosing an "unused" character as a plain delimiter (for example a control character) works only while the alphabet guarantees it never occurs; that guarantee usually breaks first.

### Language notes

- Python: two chained `str.replace` calls escape in C; `decode` collects characters in a list and joins once per string, avoiding quadratic concatenation.
- TypeScript: `replaceAll` escapes; `for (const character of encoded)` iterates code points. String concatenation with `+=` is optimized by V8.
- Java: `encode` escapes inside the same loop that copies characters; `StringBuilder.setLength(0)` reuses one buffer for every decoded string.
- Kotlin: `when` with conditions models the three cases of the decoder; `buildString` and `StringBuilder` work as in Java.
- Go: the loop indexes the string by byte and writes bytes to a `strings.Builder`; `current.Reset()` after `String()` is safe, since `String()` returns the buffer that `Reset` then drops instead of reusing.
- Rust: `chars()` walks the string and `String::push` appends; `std::mem::take(&mut current)` moves the finished string out and leaves an empty one behind, so no clone is needed.
