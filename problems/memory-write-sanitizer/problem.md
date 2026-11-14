# Memory Write Sanitizer

## Statement

An assistant stores short memories about a user, and in later conversations it reads them back into its context, each one wrapped in a pair of delimiters:

```text
<memory>
the stored text
</memory>
```

The text of a memory comes from the conversation, so it can hold anything a user typed. If it contains `</memory>`, the block closes early, and whatever follows reads as if the application had written it. If a line starts like a role marker, such as `system:`, it reads like an instruction from someone other than the user. Your job is the defensive step before a memory is stored.

Write `sanitizeMemory(text, maxLength)`. It runs three steps, in this order:

1. **Neutralize the delimiters.** A delimiter is `<memory>` or `</memory>`, in any mix of upper and lower case. Remove every one. A removal can join the text on its two sides into a new delimiter, as in `<mem<memory>ory>`, so keep removing until the text holds none.
2. **Cap the length.** When the text from step 1 is longer than `maxLength` characters, keep its first `maxLength` characters.
3. **Flag role markers.** The lines of the text from step 2 are its pieces between `"\n"` characters, numbered from 1, empty ones included. A line is flagged when, after any spaces and tabs at its start, it begins with one of the role markers `system`, `assistant`, `developer` or `tool`, in any mix of upper and lower case, followed directly by `:`. A flagged line is **kept**, not removed: the flag lets the application decide, and a false alarm loses nothing.

Everything else stays exactly as it was: letter case, spaces, tabs, blank lines, and any `<` or `>` that is not part of a delimiter.

## Input

- `text`: the memory as it came from the conversation.
- `maxLength`: the most characters the stored memory may have.

## Output

A list whose first entry is the text to store. The flags follow it, in the order of the steps:

- `"delimiters removed"`, when step 1 removed at least one delimiter;
- `"truncated"`, when step 2 cut the text;
- `"line <n>: <marker>"` for each flagged line, in line order, with the marker in lowercase, such as `"line 2: system"`.

## Examples

### Example 1

<!-- case: ex1 -->

The second line starts with `system:`, so it is flagged. It stays in the stored text: the memory may be harmless, and the application decides what to do with it.

### Example 2

<!-- case: ex2 -->

`</memory>` would have closed the block early, so it is removed. The next line starts with `Assistant:`, which matches in any letter case, and its flag names the marker in lowercase.

### Example 3

<!-- case: ex3 -->

The text is 36 characters long, and only the first 20 are kept.

## Constraints

- `0 <= text.length <= 2000`, and `1 <= maxLength <= 2000`.
- `text` holds printable ASCII characters, spaces, tabs and `"\n"`, and nothing else.

## Follow-ups

- Removing delimiters changes what the user wrote. When would you escape them instead, for example as `&lt;memory&gt;`, and what must the code that reads the memory back then do?
- A model may also treat `< /memory >` or a delimiter split by a line break as a closing tag. How would you widen step 1 without removing ordinary text?
- The flags go to the application. What should it do with a memory that has three flagged lines: store it, ask the user, or store it with a warning that the context shows?

## Hints

### Hint 1

Do the steps in the stated order and check each result against the next step: the length counts the text without its delimiters, and the flags read the text that will actually be stored.

### Hint 2

Removing every delimiter once is not enough. Either repeat until nothing changes, or scan once with a stack and drop a delimiter the moment its `>` arrives.

### Hint 3

Match the role markers on each line from its start, and compare the letters without regard to case.
