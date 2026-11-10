# Chunking With Overlap: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sentence-end-table | optimal | O(L + c) | O(t + c) | default answer |

`L` is the length of the text, `t` the number of tokens and `c` the number of chunks.

## Approach: sentence-end-table (Find the tokens once and look up the last sentence end of each window in a table)

### Intuition

Two things make chunking fiddly: offsets and the end of the loop. Both get easier once the text has been turned into a list of token spans. From then on the work is on token indexes, where a chunk is a pair `(s, e)`, the overlap is `e - overlap + 1`, and the text only comes back to turn a pair of indexes into a pair of offsets.

The cut itself is a question about one window: what is the last sentence end in tokens `s + overlap` to `s + maxTokens - 1`? Scanning the window backwards answers it. A table that holds, for every token, the last sentence end at or before it answers it with one lookup: read the table at the window's last token, and check that the answer is not before `s + overlap`.

The lower bound is what keeps the loop moving. A chunk that ends before `s + overlap` holds `overlap` tokens or fewer, so the next chunk would start at `s` again, or before it.

### Algorithm

1. If `overlap >= maxTokens`, return an empty list.
2. Find every token's start and end offsets, in order.
3. Build the table: for each token, the index of the last token at or before it that ends a sentence, or -1.
4. Start at `s = 0`. While the last chunk has not reached the final token:
   1. If `s + maxTokens - 1` reaches the final token, the chunk ends at the final token.
   2. Otherwise read the table at `s + maxTokens - 1`. If the answer is at least `s + overlap`, the chunk ends there; if not, it ends at `s + maxTokens - 1`.
   3. Write `[start of token s, end of the chunk's last token]`, and set `s` to that last token's index minus `overlap`, plus 1.

### Correctness

The table entry at the window's last token is the last sentence end at or before it. If that entry is at least `s + overlap`, it lies in the allowed range and nothing after it in the window ends a sentence, so it is the cut the statement asks for. If it is smaller, no token in the allowed range ends a sentence, and the chunk is cut at `maxTokens`. Either way the chunk ends at `e >= s + overlap`, so the next start, `e - overlap + 1`, is greater than `s`, and the loop ends. It ends exactly when a chunk reaches the final token, which is the statement's last chunk, so no chunk is made of the previous chunk's shared tokens alone.

### Complexity

- Time: O(L + c) — one pass over the text finds the tokens, one pass over them builds the table, and each chunk costs one lookup.
- Space: O(t + c) — the spans and the table hold one entry per token, and the result one pair per chunk.

### Trade-offs

Scanning each window backwards for a sentence end is just as correct and costs `O(maxTokens)` per chunk, which is fine for the sizes here. The table matters when the overlap is large: with `overlap = maxTokens - 1` there is a chunk per token, and the scan would read the window again for each of them.

Character offsets cost nothing extra and are what a citation needs. Returning chunk texts instead would lose where they came from, and searching for a chunk's text in the document to find it again breaks on repeated passages.

A sentence rule this simple misfires on abbreviations and decimal points, and real pipelines use better ones. What carries over is the shape: find candidate boundaries, prefer the best one in the window, and fall back to a hard cut.

### Pitfalls and edge cases

- **The overlap is off by one.** The next chunk starts at `e - overlap + 1`, so exactly `overlap` tokens are shared. Starting at `e - overlap` shares one too many, and `e - overlap + 2` one too few (`h1`, `h10`, `h17`).
- **A trailing chunk of shared tokens.** Looping while the next start is inside the text adds a final chunk that is only the end of the previous one. Stop when a chunk reaches the final token (`h1`, `h2`, `h14`).
- **The first sentence end instead of the last.** It makes chunks shorter than they need to be (`h8`, `h13`).
- **A sentence end inside the overlap.** Cutting there means the next chunk starts where this one did, and the loop never ends. Only a sentence end at `s + overlap` or later counts (`h9`, `h10`).
- **Cutting the last chunk at a sentence.** When the rest fits, it is one chunk, whatever sentence ends it holds (`h14`).
- **What ends a sentence.** Only the token's last character counts, so `e.g.` ends one and `3.5` and `noted.)` do not (`h13`).
- **Offsets.** They index the text as written, with runs of spaces, tabs and line breaks, and skip leading and trailing whitespace. Offsets computed as if the tokens were joined by single spaces are wrong after the first double space (`h7`, `h12`, `h15`).
- **Refusing.** `overlap >= maxTokens` would loop forever, so it returns an empty list, as do an empty text and a text of whitespace (`ex3`, `h3`, `h4`, `h5`, `h6`).
- **Small values.** One token per chunk with no overlap, and a text of one token (`h15`, `h19`).

### Language notes

- Python: `re.finditer(r"[^ \t\n\r]+", text)` gives each token's `span()` directly. `str.split()` gives the tokens but not where they are.
- TypeScript: a global regular expression's `exec` loop gives `match.index` and the match's length. The pattern is created inside the function, since a global pattern keeps its `lastIndex` between calls.
