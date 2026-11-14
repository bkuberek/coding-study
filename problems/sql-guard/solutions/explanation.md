# SQL Guard: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| token-rules | optimal | O(n s) per call, s the sources of the query | O(n + a) | default answer; one tokenizer serves every rule, and a small parser serves the rules that need the structure of the query |

Here `n` is the length of the text, `s` the number of sources (tables with their aliases) in the query, and `a` the size of the allowlist.

## How the design grows level by level

| Level | Change | What the design adds |
|-------|--------|----------------------|
| 1 | Tokens and statements | A scanner that turns the text into tokens with their positions, and a split of the tokens into statements |
| 2 | One read-only statement | Three loops over tokens: the first word of each statement, the forbidden keywords, the comments that a server may run |
| 3 | An allowlist | A recursive-descent parser for a small grammar that records the sources and the names it sees, and a second pass that resolves the names |
| 4 | Limits and placeholders | The positions of the tokens, to edit the original text in place, and a flag in the parser that marks the conditions |

The early choice that matters is to give every token its start and end in the original text. Levels 1 to 3 only need the token kind and text, and a first version that drops the positions answers them correctly. Level 4 then has to rebuild the text from tokens, which loses the exact spacing and comments, or to scan again to find where a number was.

## Approach: token-rules (One tokenizer, token rules for the early levels and a small recursive-descent parser for the later ones)

### Intuition

A check that reads characters has to guess where words begin and end, and it guesses wrong in exactly the places an attacker chooses: after a quote, inside a comment, next to a semicolon. A check that reads *tokens* makes those decisions once and in one place. The scanner decides, by fixed rules, what is a string, what is a comment and what is a word, and every later rule asks the tokens. The rules are the guard's own, so the guard is only as good as its agreement with the database on them (see the trade-offs). `updated_at` is one identifier, so no rule about `UPDATE` sees it. A `DROP` inside a string is a string. A `;` inside a comment is not a token at all.

The levels then ask more and more of the token stream. Level 2 only needs to look at single tokens, so it stays a few loops. Level 3 needs to know which words are tables, which are columns and which are aliases, and that depends on the position of a word in the query, so the guard parses the query with a grammar. The grammar is small on purpose: the more of SQL it accepts, the more the guard must agree with the database about, and every disagreement is a hole.

### Algorithm

1. **Scan.** Walk the text with an index. At each position try the rules in the order of the table of level 1: blanks are skipped; `--` and `/*` start a comment (before the symbols `-` and `/`); `'` and `"` start a string or a quoted name, which ends at the first quote that is not doubled; a digit, or a point followed by a digit, starts a number, which is an error if a letter or `_` follows it; a letter or `_` starts a word, looked up in the keyword set after converting to capitals, with the one-letter-prefix check for `'`; then `;`, the placeholders, and the symbols with the two-character ones first. Anything else, and every unfinished piece, stops the scan with an error code. Each token keeps `kind`, `text`, `start` and `end`.
2. **Statements.** Split the tokens at the semicolon tokens, drop the comments, and drop the empty groups. `check` reports the lexical error, or `empty`, or the count when it is more than one.
3. **Read-only.** For each statement look at the first token; for each keyword token look in the forbidden set; for each comment token look for the `/*!` prefix. Add each row only if it is not already in the answer.
4. **Parse.** One method per line of the grammar, reading from a shared position with `peek` and `take`. A failure raises a syntax error that carries the text of the token being looked at. While parsing, record without deciding: the sources as pairs `(source name, table)`, the aliases of the select list, and an ordered list of events (a wildcard, a call, a column with its qualifier). When an `ORDER BY` item is a single identifier token equal to an alias, drop the event it just recorded.
5. **Names.** Report the sources in order (`table-not-allowed`, then `duplicate-source`), then resolve the events in order: calls against the five aggregate names, qualified columns against the first source with that name, unqualified columns by counting the sources that are allowed and hold the column.
6. **Limit.** Re-parse and keep the token of the `LIMIT` number, the end of the token before `OFFSET`, and the end of the last token. Edit the original string at those positions. Compare the digits of a `LIMIT` as a number of any length.
7. **Placeholders.** Re-parse with a flag that is on while the parser reads the expression of a `WHERE`, a `HAVING` or an `ON`, collect the text of every number and string token taken while it is on, and classify each against `userValues`.

### Correctness

The scanner is a partition: each position is consumed by exactly one rule, the first that fits, and every rule consumes at least one character, so the loop ends and the tokens cover the text apart from blanks. The rules for quoted pieces look for the first closing quote that is not part of a doubled pair, which is the definition in the statement, so a quote inside a string can never end it early and a `;`, a keyword or a comment marker inside a string is never seen as one. Because comments are tokens and are removed before the statements are formed, a semicolon in a comment does not split anything.

Level 2 is a statement about tokens, and the loops read tokens, so a forbidden word in a string, a quoted name or a comment cannot trigger it, and a forbidden word as a keyword cannot be missed, whichever statement or place it is in. The `/*!` rule is the one place where a comment is looked at, because it is the one kind of comment that a server may execute.

The parser is a recursive-descent reading of a grammar without left recursion (the operators are folded in loops), so it consumes a token at every step it makes, and it accepts exactly the statements of the grammar. The allowlist pass is a total function of the sources and the events, so the findings follow the table of the statement; their order is the order of the sources and then of the events, which is the order of the tokens. A syntax error stops the pass before any name is resolved, so a name finding is never reported for text that is not in the subset.

The limit edit is correct because it only touches the number token, or inserts a fixed text at a token boundary that the grammar guarantees is the end of the query body: no clause follows the last token except `OFFSET`, and `LIMIT` is always before it. A string or comment that looks like `limit 1` is a token of another kind and is never considered.

### Complexity

- Time: O(n s) per call, s the sources of the query — the scan is linear in the text; the statements, the read-only rules and the parse are linear in the number of tokens; resolving an unqualified column looks at each source once, so the name pass costs O(e s) for e events, and e is at most the number of tokens. The only superlinear part is that product, with s at most n.
- Space: O(n + a) — the tokens, the events and the sources are linear in the text, and the allowlist holds the allowed names, a in total.

### Trade-offs

- A token-level guard reads the text the way the guard says. A database reads it the way it says. Where they differ (whether block comments nest, whether `--` needs a space after it, whether a backslash escapes a quote, what a comment that starts with an exclamation mark means), an attacker writes a text that one reads as a comment or a string and the other as code. The subset refuses some of what it cannot model: a letter prefix before a quote, a `/*!` comment, `WITH` and `INTO`. It does not refuse everything, and two disagreements are known and left open on purpose. Both queries below pass `checkReadOnly` and `checkAccess` (with `users`, `id` and `name` allowed), and each is read as code by one family of databases:
  - `SELECT id FROM users WHERE name = '\'' ; DROP TABLE users; -- '`. The guard treats a backslash as an ordinary character and `''` as an escaped quote, so it sees one string that runs to the last quote, and one statement. A database in whose default mode a backslash escapes a quote ends the string after `\'`, finds the `;`, and, if the connection accepts several statements in one call, runs `DROP TABLE users`.
  - `SELECT id FROM users WHERE id = 1 --1; DROP TABLE users`. The guard sees a comment from `--` to the end of the line. A database that wants whitespace after `--` reads `1 - -1`, then `;`, and runs the `DROP` under the same condition.

  They show why a lexical guard is one layer and not the defense. The other layers each stop them: parameters, because a value passed separately never becomes text and so cannot end a string or start a comment; a read-only database role, because the `DROP` fails for lack of privilege; least privilege, because the role cannot touch the table anyway; and the database's own parser, because it counts statements the way the database does. The guard could be made stricter for these two (refuse a backslash inside a string, require whitespace after `--`), and each such rule closes one gap while the next dialect detail opens another, which is why the durable fix is to ask the database in addition.
- A parser for a subset is stricter than a scan for words, and it refuses more honest queries (no `WITH`, no subquery, no `CASE`, only five functions). That is the right default for a guard, since a refused query can be rewritten by the model and a wrong acceptance cannot be taken back; the cost is paid in a second model call.
- An allowlist beats a denylist for the same reason: a denylist has to name every bad thing, an allowlist only names the good things. This guard uses both on purpose. The forbidden keywords catch a write the grammar might one day be extended to accept, and the allowlist decides which data is readable.
- Names are compared without regard to case, even for quoted names. A real database does not do that: it folds unquoted names to one case and keeps the case of quoted names, and the case it folds to depends on the database. The simplification keeps the problem about the guard and not about naming rules, and it is safe only as long as the database's own names agree with it. In PostgreSQL, for example, `"Users"` and `users` are different tables. With `users` allowed, `SELECT id FROM "Users"` passes the guard, which folds the name to `users`, and reads a table that the allowlist never named. The condition is that no two tables, and no two columns of one table, in the real database differ by case alone; a guard for such a database should compare quoted names exactly and fold only unquoted ones.
- Neither a row limit nor an allowlist bounds the cost of a query: a join of three large tables can run for hours and return ten rows. Time limits, resource limits and a read-only database role belong to the database, not to this guard.

### Pitfalls and edge cases

- Level 1: a doubled quote is one quote in the content and does not end the string; a backslash is not special. `/*/` is not a closed comment, and `/* /* */ */` is one comment followed by `*` and `/`. A number followed by a letter is an error and not two tokens. A `$` or `:` that does not start a placeholder is an error. The text `a--b` has a comment in it.
- Level 2: the statement count and the first-word rule are different findings, both reported. `SELECT 1; SELECT 2` has only `multiple-statements`. A forbidden word is reported once however many times it appears, and a word like `REPLACE` is refused even when it is a harmless function: the guard cannot know. A quoted name is never a keyword, so `"update"` passes.
- Level 3: after an alias the table name is not a source name. The same source name twice is reported, and the first one wins for qualified lookups. A name in the select list is checked as a column even when an `ORDER BY` item with the same name is an alias reference. A wildcard is refused because the allowlist is about the columns that the guard can see in the text, and `*` stands for the ones it cannot. `count` without a parenthesis is a column.
- Level 4: a limit goes before an `OFFSET`, before a `;` and before a trailing comment, never after them. A `LIMIT` of `005` that is already low enough stays `005`. A number with more digits than a machine integer must still be compared as a number. `LIMIT ?` is refused at level 3, since the guard cannot know what it limits. User values match by exact text, and a sign is a separate token.

### Language notes

- Python: integers have any size, so `int(token.text) > max_rows` is exact for any `LIMIT`. `str.upper()` on ASCII words is what the keyword lookup needs, and slices of the original string give the in-place edits.
- TypeScript: `Number` loses precision above 2^53, so the `LIMIT` digits are compared with `BigInt`. Strings are indexed by UTF-16 unit, which is the same as by character for the ASCII that the scanner accepts; any other character outside strings, quoted names and comments is an `unexpected-character` error (inside them, any character is accepted). The default `Set` and `Map` compare strings by value, so no key function is needed for names.

## Further reading

- [SQL Injection Prevention Cheat Sheet, OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html): its primary defenses are parameterized queries and allow-list input validation, manual escaping is strongly discouraged, and least privilege is listed among the additional defenses that limit the damage when something else fails.
- [LLM10:2026 Improper Output Handling (2025: LLM05), OWASP Top 10 for LLM Applications 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/): the entry for model output that is passed on without enough validation and sanitization. Its examples include model-written SQL that is executed without proper parameterization, and its mitigations include parameterized queries or prepared statements for all database operations that involve model output.
- [PostgreSQL documentation, Lexical Structure](https://www.postgresql.org/docs/current/sql-syntax-lexical.html): a quote inside a string constant is written twice; `--` comments run to the end of the line; block comments nest in PostgreSQL "as specified in the SQL standard but unlike C"; an `E` before a quote makes a string in which a backslash begins an escape; and quoting an identifier makes it case-sensitive, whereas unquoted names are folded to lower case (`"Foo"` and `foo` are different names). The table of level 1 agrees on the doubled quote and on `--`. It makes the opposite choice only for block comments, which end at the first `*/` and do not nest, and it refuses the `E` prefix instead of modelling it. Its case-insensitive names differ from the last point, as the trade-offs say.
- [MySQL Reference Manual, Comments](https://dev.mysql.com/doc/refman/8.4/en/comments.html): the `--` style needs whitespace or a control character after the second dash, nested comments are not supported, and the code in a `/*! ... */` comment is parsed and executed by that server and ignored by others.
- [MySQL Reference Manual, String Literals](https://dev.mysql.com/doc/refman/8.4/en/string-literals.html): inside a string, a backslash is an escape character unless the `NO_BACKSLASH_ESCAPES` mode is on, and a doubled quote is an alternative way to write a quote; two parsers can read the same text as different strings, which is the first query of the trade-offs.
- [PostgreSQL documentation, WITH Queries: Data-Modifying Statements in WITH](https://www.postgresql.org/docs/current/queries-with.html): `INSERT`, `UPDATE`, `DELETE` or `MERGE` can appear inside a `WITH`, and such a statement is executed even if the main query does not read its output; the reason why the subset does not accept a statement that starts with `WITH`.
- [PostgreSQL documentation, SELECT INTO](https://www.postgresql.org/docs/current/sql-selectinto.html): "SELECT INTO creates a new table and fills it with data computed by a query"; the reason why `INTO` is a forbidden word.
- [PostgreSQL documentation, SET TRANSACTION](https://www.postgresql.org/docs/current/sql-set-transaction.html): a read-only transaction disallows the write and definition commands it lists, and the page states that this is a high-level notion of read-only that does not prevent all writes to disk. A database-side read-only mode is a second layer, not a replacement for the first.
