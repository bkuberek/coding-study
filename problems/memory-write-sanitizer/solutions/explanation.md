# Memory Write Sanitizer: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| stack-scan | optimal | O(n) | O(n) | default answer |

`n` is the length of `text`.

## Approach: stack-scan (Remove delimiters on a stack in one pass then cut and flag the lines)

### Intuition

Text that will be read back into a model's context is untrusted input crossing into a structured format, like user input crossing into HTML or SQL. The defense has the same shape: first make sure the input cannot change the structure around it (the delimiters), then bound its size, then report what looks suspicious without silently changing it.

The tricky part is the first step. Removing a token can create it: `<mem<memory>ory>` holds one delimiter, and removing it leaves `<memory>`. One pass of "replace all" is not enough. You can repeat it until nothing changes, which is simple and correct but costs a pass per layer of nesting, so an input built to nest deeply makes it quadratic. A stack does it in one pass: push each character, and when a `>` arrives, check whether the top of the stack now spells a delimiter; if it does, pop it. The characters under the top never change afterwards, so a delimiter can only ever form at the top, and it is removed the moment it forms.

Order matters for the other two steps. The length cap applies to what will be stored, so it comes after the delimiters are gone. The flags describe what will be stored, so they read the text after the cut: a removal can move a role marker to the start of a line, and a cut can remove a flagged line or cut its marker short.

### Algorithm

1. Walk the text one character at a time, pushing each onto a stack. When the character is `>`, compare the last 8 characters (for `<memory>`) and the last 9 (for `</memory>`), lowercased, with the delimiters; on a match, pop those characters and note that a delimiter was removed.
2. Join the stack. If it is longer than `maxLength`, keep its first `maxLength` characters and note the cut.
3. Split the result on `"\n"`. For each line, numbered from 1, match spaces and tabs, then a marker word, then `:`, from the start of the line and ignoring case; on a match, add `line <n>: <marker>` with the marker lowercased.
4. Return the text, then `delimiters removed` if step 1 removed one, `truncated` if step 2 cut, and the line flags in order.

### Correctness

Removing delimiters is a rewriting system: any occurrence of `<memory>` or `</memory>` may be deleted, until none is left. No delimiter overlaps another (each starts with `<` and contains no other `<`), and neither is inside the other, so whichever occurrence is deleted first, the end result is the same. "Keep removing until none is left" therefore has one answer, and any strategy that only deletes delimiters and stops when none is left finds it.

The stack is such a strategy. Invariant: after each character, the stack holds no delimiter. Pushing a character can only create a delimiter that ends at the top, and since every delimiter ends with `>`, checking only on `>` is enough; popping it restores the invariant, and what lies below the top was already free of delimiters. At the end the stack holds none, and every pop deleted a real occurrence, so it is the unique result.

Step 2 keeps a prefix, which cannot create a delimiter, since a prefix of text with no delimiter has none. Step 3 reads exactly the stored text, so a flag is raised for a line if and only if the stored line starts with a marker.

### Complexity

- Time: O(n) — each character is pushed once and popped at most once, and the check on `>` compares at most 9 characters; the cut and the line scan are linear too.
- Space: O(n) — the stack and the result.

### Trade-offs

- Repeating a global replace until nothing changes is the easiest correct answer, and fine for short memories. Its worst case is a pass per nesting level, O(n^2) for a crafted input, and a sanitizer is exactly the code an attacker gets to feed. The stack keeps the cost linear for any input.
- Escaping the delimiters (`&lt;memory&gt;`) instead of removing them keeps the user's text recoverable and can never create a new delimiter, since it removes nothing. The reader of the context must then understand the escape, and the stored text grows. Removal was chosen here because a memory is a note, not a document.
- Escaping every `<` and `>` in the text is the broadest defense against the wrapper format, but it changes ordinary text such as `a < b`, which the statement keeps.
- Flagging and not dropping is deliberate: a pattern list is never complete and always has false alarms (`user:` is left out because memories about the user often start that way), so the decision belongs to the application, which can see the whole conversation.

### Pitfalls and edge cases

- **Case-sensitive matching.** `</Memory>` closes the block just as well (`h1`).
- **Replacing only the first match.** TypeScript's `replace` with a string pattern changes only the first occurrence, and so does a regex without the `g` flag (`h2`).
- **One pass of removal.** It leaves a delimiter that the pass itself joined together (`h3`, `h4`).
- **Removing too much.** Look-alikes such as `< memory>`, `<memories>` or a lone `<memory` are ordinary text (`h5`).
- **Loose role markers.** The marker must be at the start of the line after spaces and tabs only, and followed directly by a colon, so `systems:`, `the system:` and `system :` are not flagged; `user:` is not a marker (`h6`).
- **Flagging the original text.** A removal can put a marker at the start of a line (`h7`), and the cut can remove a flagged line or cut its marker short (`h11`, `h12`).
- **Cutting before removing.** The limit counts the stored text, so a text that fits once its delimiters are gone is not cut (`h8`, `h13`).
- **Off by one at the limit.** A text of exactly `maxLength` characters stays whole (`h9`, `h10`).
- **Tidying the text.** Trimming spaces, dropping blank lines or changing case alters the memory (`h14`); dropping a flagged line hides it from the application (`h17`).
- **Line numbers.** They count from 1 and include blank lines (`h16`), and an empty text is one empty line, with no flags (`h15`).

### Language notes

- Python: `re.match` anchors at the start of the line, and `re.IGNORECASE` handles the marker's case; the constraint to ASCII matters, since Python folds some non-ASCII letters (the Kelvin sign, U+212A, matches `k`). `str.split("\n")` keeps the empty last line after a trailing `"\n"`, while `splitlines()` drops it and also splits on other line breaks.
- TypeScript: a regex with the `i` flag and `^` serves the markers. `kept.length -= delimiter.length` pops several characters from the stack at once. `for (const character of text)` walks code points, which for ASCII are the characters that `length` counts.
