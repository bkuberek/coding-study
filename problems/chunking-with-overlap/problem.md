# Chunking With Overlap

## Statement

Before documents can be searched by meaning, they are cut into chunks small enough to embed, and each chunk keeps its place in the source, so that an answer can cite it. A chunk that ends mid-sentence loses half a thought, and two chunks that share a few words keep a thought that straddles the cut. Write `chunkText`, which cuts a text into chunks of at most `maxTokens` tokens, each sharing `overlap` tokens with the one before, and returns where each chunk starts and ends.

**Tokens.** A token is a maximal run of characters that are not whitespace, where whitespace is the space, the tab, `\n` and `\r`. A token starts at the index of its first character in `text` and ends at the index just past its last character.

**Sentence ends.** A token ends a sentence when its last character is `.`, `!` or `?`. The rule is deliberately simple: `e.g.` ends a sentence, and `3.5` and `noted.)` do not.

**Chunks.** A chunk is a run of consecutive tokens. Build them in order, starting at token 0:

1. A chunk starts at token `s`. If the tokens from `s` to the last token number at most `maxTokens`, the chunk takes all of them and is the last chunk.
2. Otherwise the chunk ends at a token from `s + overlap` to `s + maxTokens - 1`: at the **last** of those that ends a sentence. Starting at `s + overlap` guarantees that the chunk holds more than `overlap` tokens, so the next chunk starts further on. If none of them ends a sentence, the chunk ends at token `s + maxTokens - 1`, cutting the sentence.
3. If the chunk ends at token `e`, the next chunk starts at token `e - overlap + 1`, so the two share exactly `overlap` tokens.

A chunk is returned as `[start, end]`: where its first token starts and where its last token ends. `text[start:end]` in Python, or `text.slice(start, end)` in TypeScript, is the chunk with its inner whitespace as written.

**Refusals.** A chunk can only move past the one before it if `overlap` is smaller than `maxTokens`. When it is not, refuse by returning an empty list. A text without tokens has no chunks, so it also gives an empty list.

## Input

- `text`: the text to cut, in ASCII.
- `maxTokens`: the most tokens a chunk may hold.
- `overlap`: how many tokens consecutive chunks share.

## Output

One `[start, end]` pair per chunk, in order.

## Examples

### Example 1

<!-- case: ex1 -->

The first window holds `The cache was cold. Every request`, and the last sentence end in it is `cold.`, so the first chunk is `The cache was cold.`. The next chunk starts one token back, at `cold.`, and ends at `it.`. The rest, `it. Then the warmer ran.`, is five tokens and fits.

### Example 2

<!-- case: ex2 -->

One sentence of eleven tokens never fits in four, so each chunk is cut at four tokens: `Retries back off exponentially`, `exponentially with jitter until`, `until the budget runs`. Each starts on the last token of the one before. The rest, `runs out.`, fits.

### Example 3

<!-- case: ex3 -->

An overlap of 2 with chunks of 2 tokens would never move forward, so the call is refused.

## Constraints

- `0 <= text.length <= 10^5`, and `text` holds printable ASCII characters, spaces, tabs, `\n` and `\r`.
- `1 <= maxTokens <= 10^4`.
- `0 <= overlap <= 10^4`.

## Follow-ups

- Count tokens with a model's tokenizer instead of whitespace. What changes, and why do character offsets matter even more then?
- Prefer a paragraph break to a sentence end, and a sentence end to a cut. How would you rank several kinds of boundary in one pass?
- Make every chunk but the first start at a sentence as well. What does that do to the overlap and to the number of chunks?
- After a small edit to a long document, which chunks can you keep, so that their embeddings need not be computed again?

## Hints

### Hint 1

Find every token's start and end once. Everything after that works on token indexes, and offsets come back only when a chunk is written out.

### Hint 2

For each token index, record the last sentence end at or before it. The end of a chunk is then one lookup at `s + maxTokens - 1` and one comparison with `s + overlap`.

### Hint 3

Stop when a chunk reaches the last token, not when the next start passes it. Otherwise the shared tail of the last chunk becomes a chunk of its own.
