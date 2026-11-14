# SQL Guard

## Statement

Build `SqlGuard`, the check that stands between SQL text written by a language model and the database that would run it. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working as they did.

**Why check at all?** SQL is the language in which programs talk to a database. A query that starts with `SELECT` reads data (`SELECT name FROM people WHERE age > 30`); other statements change it (`INSERT`, `UPDATE`, `DELETE`) or its structure (`CREATE`, `DROP`, `ALTER`). A program that lets a model turn a question in plain words into SQL and runs the result holds a risk: the model may be wrong, or it may have been misled by text it read on the way (a web page or a document can carry instructions that the model follows), and the database does whatever the text says. The text must be treated like any other input from outside, however friendly its author. The OWASP list of risks for applications built on language models names this as improper output handling: model output used by a later step without being checked first.

**Why not search the text for bad words?** The first idea is to reject a query when the lower-cased text contains `delete`, `drop`, `update` and so on. It fails in both directions. It rejects honest queries: the column `updated_at` contains `update`, and the note `'please delete me'` is only a piece of data. And it accepts dangerous ones, because the list is never complete, and because it cannot count statements or tell a comment from code. The reliable way is to read the text the way the database does: first cut it into *tokens* (words, numbers, quoted strings, symbols and comments), then look at the tokens. That is what this problem builds, from the cutting to the rules.

**One layer of several.** A guard like this is *defense in depth*: one layer among others, and not a replacement for them. A real system also connects with a database account that can only read the tables it needs (least privilege), runs the query with the database's own read-only mode and time and size limits, passes values as parameters and not as pieces of text, and, where it can, checks the query with the database's own parser, which knows every detail of its own dialect. A hand-written guard can disagree with the real parser about where a string or a comment ends, and an attacker lives in that disagreement. This problem makes one choice for each detail, states it, and keeps the guard small enough to hold in your head. Some of those choices differ from some databases, and the explanation shows two queries that the guard accepts and one family of databases reads as code: that is the reason for the other layers, and not a bug to fix in the tokenizer.

**The subset.** The guard does not try to understand all of SQL. It understands a small, precisely specified part, and everything outside it is refused. Level 1 gives the vocabulary (the tokens), level 2 the statements that are allowed, level 3 the queries that fit a small grammar and use only tables and columns that were allowed, and level 4 two helpers for the application around the guard: one makes sure a query returns a bounded number of rows, the other finds values that should have been placeholders.

Aim to finish in 150 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 40, level 2 by 65, level 3 by 120 and level 4 by 145, keeping the last minutes for a final run.

## Input

- `SqlGuard()`: creates a guard with no table allowed.
- `sql` is any string of at most 2000 characters. It is read exactly as given, including line breaks.
- A table or column name given to `allowTable` is 1 to 30 letters (`a` to `z`, either case), digits and `_`, not starting with a digit.
- `maxRows` is from 1 to 1000000.
- Each level's section describes the methods it adds and their parameters.

## Output

Most methods return **findings**: a list of rows `[code, detail]` of two strings. An empty list means the guard found nothing wrong. A row is never repeated in one answer: when the same row would come twice, only its first place stays. Methods that tokenize return rows `[kind, text]`. Texts are compared exactly, so `SELECT` and `select` are different texts; where a name is compared, the section says how.

## Level 1: Tokens and statements

The guard reads the text from left to right. At each position, the first of these rules that fits decides what comes next. A *word* is a letter or `_` followed by any number of letters, digits and `_`, with letters meaning `a` to `z` and `A` to `Z`.

| Starts with | Kind | What it covers | `text` of the row |
|-------------|------|----------------|-------------------|
| a blank (space, tab, line feed, carriage return) | none | skipped | none |
| `--` | `comment` | up to, not including, the next line feed or carriage return, or the end of the text | the comment as written, with `--` |
| `/*` | `comment` | up to and including the first `*/` after the `/*` (comments do not nest, and `/*/` is not closed) | the comment as written |
| `'` | `string` | up to the closing `'`; a doubled `''` inside is one quote and does not close it; a backslash is an ordinary character | the content, each `''` read as `'` |
| `"` | `identifier` | a quoted name, with the same doubling rule for `""` | the content, each `""` read as `"` |
| a digit, or `.` followed by a digit | `number` | digits, then optionally `.` and digits (`.5` is a number; `1.` is the number `1` and then a symbol) | the number as written |
| a word | `keyword` or `identifier` | a word whose capitals are in the keyword list is a `keyword`, any other word is an `identifier` | a keyword in capitals, an identifier as written |
| `;` | `semicolon` | the character | `;` |
| `?`, `$` and digits, or `:` and a word | `placeholder` | the marker of a value that is passed separately | the marker as written |
| `<=` `>=` `<>` `!=` `\|\|`, or one of `( ) , . * + - / % = < >` | `symbol` | the longest one that fits | the symbol |

The keyword list has two parts. The words of the **query** part are `SELECT FROM WHERE GROUP BY HAVING ORDER LIMIT OFFSET AS JOIN INNER LEFT RIGHT FULL OUTER CROSS ON AND OR NOT NULL IS IN LIKE BETWEEN DISTINCT ASC DESC UNION ALL TRUE FALSE WITH`. The words of the **forbidden** part, explained at level 2, are `INSERT UPDATE DELETE MERGE REPLACE DROP CREATE ALTER TRUNCATE RENAME GRANT REVOKE CALL EXEC EXECUTE COPY ATTACH DETACH PRAGMA VACUUM SET INTO`. A quoted name is never a keyword: `"select"` is an identifier.

The scan stops at the first of these **lexical errors**, and the answer holds the tokens before it, followed by one last row `["error", code]`:

| Code | When |
|------|------|
| `unterminated-string` | a `'` is never closed |
| `unterminated-identifier` | a `"` is never closed |
| `empty-identifier` | `""` with nothing between the quotes |
| `unterminated-comment` | a `/*` is never closed |
| `malformed-number` | a number is followed directly by a letter or `_` (`1abc`, `0x1F`, `1.5e3`) |
| `prefixed-string` | one of the letters `E`, `N`, `X` or `B` (either case), as a word of its own, is followed directly by a `'`: several databases give such a prefix a meaning, such as backslash escapes, that this guard does not model |
| `unexpected-character` | any other character, such as `` ` ``, `[`, `@`, `#`, `!` alone, `|` alone, `$` alone, `:` alone or a character that is not ASCII |

A **statement** is the run of tokens between two semicolons. Comments are not part of a statement, and a run with no token is not a statement. So `SELECT 1;` is one statement, `;;` is none and `SELECT 1; SELECT 2` is two.

- `tokenize(sql)`: the rows `[kind, text]` of all tokens, in order, comments included, and the error row at the end when there is one. `""` gives `[]`.
- `check(sql)`: the findings of this level. If the text has a lexical error, the answer is the single row `["lex-error", code]`. Otherwise, if it has no statement, `["empty", ""]`, and if it has more than one, `["multiple-statements", count]` with the count as decimal text. Otherwise `[]`.

A guard that accepts only one statement closes the oldest trick of the trade: `SELECT 1; DROP TABLE users` is two statements, the second one chosen by the attacker.

### Example 1

<!-- case: ex1 -->

The tokens of a query with an escaped quote in a string (`'O''Brien'` is the text `O'Brien`), a comparison, a closing semicolon and a comment. Each word is classified, the comment is a token of its own, and `check` finds one statement.

### Example 2

<!-- case: ex2 -->

Two statements are refused, and the count is read from tokens: a trailing `;` adds no statement, a `;` inside a string is text, and a `;` inside a comment is not even a token.

## Level 2: One read-only statement

Level 1 knows what is in the text and how many statements there are. This level adds the rule that gives the guard its purpose: the only allowed statement is `SELECT`.

- `checkReadOnly(sql)`: the findings of `check`, then, only when `check` found no lexical error and the text has a statement, these rows in this order:
  1. for each statement in the text, in order, if its first token is not the keyword `SELECT`, the row `["not-select", text]` with the text of that first token;
  2. for each token of kind `keyword` whose text is in the forbidden part of the keyword list, in order, the row `["forbidden-keyword", word]`;
  3. the row `["executable-comment", ""]` if any comment token starts with `/*!`.

  Keywords are read from tokens, so a word inside a string, a quoted name or a comment is never a keyword, and `updated_at` is one identifier. `WITH` is not allowed as a first token, which is a decision of this subset: in some databases a `WITH` clause can contain a `DELETE` or an `UPDATE`, so a query that starts with `WITH` does not have to be a read. A `SELECT` that reads from nothing but constants is still a `SELECT`.

**Three details that hide a write.** `INTO` is forbidden because in some databases `SELECT ... INTO name FROM ...` creates a new table and fills it. `REPLACE` and `SET` are forbidden although they also have harmless uses (a string function, a column called `set`): the guard errs on the side of refusing, and a model that needs a name like that can quote it (`"set"`) because a quoted name is not a keyword. And a block comment that starts with `/*!` is a comment for most databases but not for all: one family of databases runs the code inside it. The guard treats it as a finding, because a guard that skips comments would otherwise skip code.

**Why a substring search fails.** Two more methods put the naive check next to the real one. The **naive check** rejects a text when its lower-cased form contains, anywhere, one of these seven strings: `insert`, `update`, `delete`, `drop`, `alter`, `create`, `truncate`.

- `naiveCheck(sql)`: `"reject"` if the naive check rejects the text, `"allow"` otherwise.
- `contrast(sql)`: compare the naive check with `checkReadOnly`, which rejects when it returns at least one row. The answer is `"agree"` when both give the same verdict, `"false-alarm"` when the naive check rejects and `checkReadOnly` allows, and `"miss"` when the naive check allows and `checkReadOnly` rejects.

### Example 1

<!-- case: ex3 -->

`updated_at` is one identifier, so the guard has no finding, while the naive check sees `update` inside it. The same happens for `delete` in a string value and for `insert` in a comment: three false alarms, all of them honest queries.

### Example 2

<!-- case: ex4 -->

The first call gives the three findings of a smuggled second statement: there are two statements, the second does not start with `SELECT`, and `DROP` is forbidden. `DELETE FROM users` is refused as a first word and as a forbidden word. The naive check misses `SELECT * INTO copy FROM users`, because `into` is not in its list, while the guard sees the keyword `INTO`; and for `DROP TABLE users` both agree.

## Level 3: Tables and columns on an allowlist

A query can be a single `SELECT` and still read what it must not: the table of passwords, or a column with personal data. This level adds an **allowlist**: the guard knows which tables, and which columns of each, a query may use.

- `allowTable(table, columns)`: allows the table with exactly those columns. It returns `true` when the table is new and `false` when it was already allowed, in which case nothing changes. Table and column names are compared **without regard to case**, quoted or not, and are kept in lower case; a column list may be empty and may repeat a name.
- `checkAccess(sql)`: the findings of `checkReadOnly` when it finds anything, and otherwise the findings below. A guard with no allowed table allows no table.

**The grammar.** When `checkReadOnly` finds nothing, the one statement is read with this grammar. Comments are skipped; a keyword is written in capitals, and `[ ]` is optional, `{ }` is repeated zero or more times, `|` is a choice.

```text
query     := SELECT [DISTINCT] item {"," item}
             [FROM source {"," source | [joinkind] JOIN source [ON expr]}]
             [WHERE expr] [GROUP BY expr {"," expr}] [HAVING expr]
             [ORDER BY expr [ASC | DESC] {"," expr [ASC | DESC]}]
             [LIMIT integer] [OFFSET integer]
item      := "*" | expr [[AS] name]
source    := name [[AS] name]
joinkind  := INNER | LEFT [OUTER] | RIGHT [OUTER] | FULL [OUTER] | CROSS
expr      := and {OR and}
and       := not {AND not}
not       := NOT not | predicate
predicate := sum [ ("=" | "<>" | "!=" | "<" | "<=" | ">" | ">=") sum
                 | IS [NOT] NULL
                 | [NOT] LIKE sum
                 | [NOT] IN "(" expr {"," expr} ")"
                 | [NOT] BETWEEN sum AND sum ]
sum       := product {("+" | "-" | "||") product}
product   := unary {("*" | "/" | "%") unary}
unary     := ("-" | "+") unary | primary
primary   := number | string | placeholder | TRUE | FALSE | NULL
           | "(" expr ")" | column | call
column    := name ["." name]
call      := name "(" [ "*" | [DISTINCT] expr {"," expr} ] ")"
```

Here `name` is a token of kind `identifier`, `integer` is a `number` token written with digits only, and an identifier whose next token is `(` is a `call`, never a column (blanks and comments between the two do not matter, so `count (id)` and `count/**/(id)` are calls). Nothing else is accepted: no subquery, no `UNION`, no `WITH`, no `CASE`, no schema-qualified table. If the statement does not fit, the answer is the single row `["syntax", text]` with the text of the first token that does not fit, or `end of input` when the text ends too soon. Two calls have a stricter shape: `COUNT`, `SUM`, `AVG`, `MIN` and `MAX` (any case) take exactly one argument, written `expr` or `DISTINCT expr`, and only `COUNT` may take `*`; an argument that does not fit is a `syntax` row at the first token that does not fit (for `sum(*)` that token is the `*`, for `count()` it is the `)`, and for `max(a, b)` it is the `,`).

**Names.** Each `source` is a table with an optional alias. Its **source name** is the alias if there is one and otherwise the table name; once a table has an alias, the table name no longer names it. Every source of a query is visible everywhere in it, in the select list, `ON`, `WHERE`, `GROUP BY`, `HAVING` and `ORDER BY` alike. A column is **qualified** (`u.id`) or **unqualified** (`id`). The one extra rule is for output names: an `ORDER BY` item that is exactly one unqualified name, with or without `ASC` or `DESC`, and equal to an alias given in the select list, refers to that output column and has no finding. Anywhere else an alias is not a name: a name inside a bigger `ORDER BY` expression, in `WHERE`, `GROUP BY` or `HAVING` is a column.

**The findings.** Names in details are in lower case.

| Code | detail | When |
|------|--------|------|
| `table-not-allowed` | the table | a source's table is not allowed |
| `duplicate-source` | the source name | a source name was already used by an earlier source |
| `wildcard-not-allowed` | `*` | an `item` is `*`: it would return every column of the table, allowed or not, and the guard cannot see the table's real columns |
| `function-not-allowed` | the function | a `call` whose name is not `count`, `sum`, `avg`, `min` or `max` |
| `unknown-source` | the qualifier | a qualified column whose qualifier is not a source name |
| `column-not-allowed` | `table.column` for a qualified column, `column` for an unqualified one | see below |
| `ambiguous-column` | the column | an unqualified column that two or more sources could provide |

A qualified column `q.c` finds the first source whose name is `q`. If its table is allowed and `c` is not one of the table's columns, the finding is `column-not-allowed` with `q.c`. If its table is not allowed, there is no column finding: the table is already reported. For an unqualified column `c`, count the sources whose table is allowed and has the column `c`. With two or more, the finding is `ambiguous-column`. With none, it is `column-not-allowed` with `c`, unless some source's table is not allowed, in which case the column could belong to that table and nothing more is said.

The rows come in this order: first the table findings (`table-not-allowed` and `duplicate-source`), in the order of the sources in the text, and for one source the table finding before the duplicate; then the other findings in the order in which their tokens appear in the text.

### Example 1

<!-- case: ex5 -->

Two tables are allowed. A plain query and a join with aliases pass. `password` is not an allowed column of `users`, and `*` is refused. A second `allowTable("users", ...)` returns `false` and changes nothing.

### Example 2

<!-- case: ex6 -->

A table that is not allowed is reported once, and its columns are not reported on top of it. `id` is in both tables, so `FROM users, orders` leaves it ambiguous. `users.id` is fine on `FROM users`, and unknown on `FROM users u`: after the alias, the only name of the table is `u`.

## Level 4: Row limits and placeholders

Two helpers for the application around the guard. Both need the structure that level 3 found.

- `limitedSql(sql, maxRows)`: when `checkAccess(sql)` finds anything, the empty string `""`. Otherwise the text of the query with a row limit enforced, changed in place as follows, so that whitespace, comments and the final semicolon stay where they were:
  - if the query has a `LIMIT` whose number is greater than `maxRows`, the digits of that number are replaced by `maxRows` written in decimal; the number is read as an integer of any length, so `007` is 7 and 20 nines is huge;
  - if its `LIMIT` is `maxRows` or less, the text does not change at all (so `005` stays `005`);
  - if it has no `LIMIT`, the text ` LIMIT maxRows` (a space, the keyword in capitals, a space, the number) is inserted at the end of the last token before `OFFSET` when the query has an `OFFSET`, and otherwise at the end of the last token of the query. The last token never includes a trailing `;` or a comment.

  The insertion point matters. A limit appended at the very end of the text would land after a `--` comment and become part of it, and after an `OFFSET` it would be a syntax error.
- `parameterFindings(sql, userValues)`: values that came from a user should reach the database as parameters (the `?`, `$1` or `:name` placeholders of level 1), never as pieces of the query text, because a value written into the text is a way to change the meaning of the query. This method finds literals written in a place where a placeholder was expected. A **condition** is the expression of a `WHERE`, a `HAVING` or an `ON`. A **literal** is a `number` or `string` token inside a condition (including in a call or in arithmetic there). If the text is not exactly one statement that fits the grammar of level 3 (it does not need to pass the allowlist), the answer is `[]`. Otherwise the answer has one row `[kind, text]` for each literal in the order of the text, where `text` is the token's text (the decoded content for a string) and `kind` is `inlined-value` if `text` is exactly equal to one of the `userValues` and `literal` otherwise. A row is not repeated. `TRUE`, `FALSE`, `NULL` and placeholders are not literals, and neither is anything outside a condition (the select list, `GROUP BY`, `ORDER BY`, `LIMIT`).

The two kinds differ in confidence. An `inlined-value` row says that a value the user supplied was pasted into the query. A `literal` row says only that a constant is there, which may be fine (`status = 'active'`) or may be a user value that the model changed a little. A sign is a separate token, so the user value `-5` never matches the literal `5` in `a = -5`.

### Example 1

<!-- case: ex7 -->

A limit is added, a larger one is lowered, a smaller one stays, and a query that the access check refuses comes back as the empty string.

### Example 2

<!-- case: ex8 -->

The e-mail typed by the user is in the query as a string, so it is an `inlined-value`, and the constant `7` is a `literal`. With placeholders there is nothing to report. A string in the select list is not in a condition, so it is not reported.

## Constraints

- At most 200 calls per test.
- `sql` has at most 2000 characters; a query has at most 300 tokens.
- At most 20 tables are allowed, each with at most 20 columns.
- `userValues` has at most 20 entries, each at most 100 characters.
- `maxRows` is from 1 to 1000000.

## Follow-ups

- The guard accepts a query that fits its grammar and the allowlist. Which dangerous queries would still pass? Think of a join that multiplies rows without bound, a very expensive `LIKE`, and a query that is valid but asks for something the user may not see: the allowlist is about tables and columns, not about rows.
- A row limit bounds what is returned, not what is read. What would bound the work: time limits, a cost estimate, a read-only replica?
- What does it take for the guard and the database to agree on every comment and string rule? Some databases nest block comments, some require a space after `--`, some treat a backslash in a string as an escape, and some run code inside a special comment. How does each of those turn a harmless-looking query into a different one for the database? This guard refuses the special comment, treats a backslash as an ordinary character, ends a block comment at the first `*/` and lets `--` start a comment without a space after it; which of those answers would you change, and which layer would still catch what remains?
- Why is the allowlist better placed in the database, as a role that has the privileges of exactly those tables and columns? What can the guard still add to that?
- The `userValues` check finds only exact copies. How would an attacker, or a confused model, get around it, and why is "every literal in a condition is a finding" a stronger policy at the price of more false alarms?

## Hints

### Hint 1

Do not look for words in the text. Read it like a person who sorts sentences into pieces: keep a position, and at each position look at one character to decide what kind of piece starts there. A quote starts a piece that lasts until the next quote; two quotes in a row inside it mean one quote character and do not end it. Digits start a number, a letter starts a word, a space is skipped. Write `tokenize` first, and test it on very small inputs, one kind of piece at a time.

### Hint 2

A string, a quoted name and a block comment have the same shape: find where the piece ends, take what is between, and report an error if the text ends first. Check your order of rules: `--` and `/*` must be tried before the symbols `-` and `/`, and the two-character symbols before the one-character ones. A line comment ends before the line break, not after it.

### Hint 3

Turn a word into a keyword by looking up its capital letters in a set; an identifier keeps its own spelling. The statements are the groups of tokens between semicolon tokens, with comments dropped and empty groups thrown away. Counting them is then trivial, and a semicolon in a string or a comment never reaches the count because it was never a semicolon token.

### Hint 4

Level 2 is three small loops over tokens, not over text: one over the statements (look at the first token), one over all tokens (look at keywords), one over comments (look at their first three characters). Add each row to the answer only if it is not already there. Run the naive check on the raw text with a plain substring test, on purpose; `contrast` compares its verdict with an empty-or-not test of the guard's findings.

### Hint 5

For the grammar, write one small function per line of it, each reading tokens from a shared position and calling the functions of the lines below it. Keep two helpers: one that looks at the next token without taking it, and one that takes it. When something does not fit, stop with the text of the token you were looking at (or "end of input"). While parsing, do not decide anything about names yet: just write down what you saw, in order, as events (a column with its qualifier, a call, a `*`) and a list of the sources.

### Hint 6

With the sources and the events written down, the allowlist is a second, simple pass. First go over the sources and report their tables; then go over the events in the order they were seen. Keep the source names in a list where you can find the first one with a given name, and make every comparison on lower-cased text. For the `ORDER BY` rule, remember the aliases of the select list as you go, and when an `ORDER BY` item turned out to be one single identifier token, drop the event you just wrote if it matches an alias.

### Hint 7

Give every token the position where it starts and ends in the original text; then `limitedSql` is a cut-and-paste on the original string: replace the digits of the `LIMIT` token, or insert the new text at the end of the right token. Compare the digits of the `LIMIT` as numbers of any length (a language with fixed-size integers needs a big-integer type, or a comparison by length and then by digits). For `parameterFindings`, keep a flag that is on while the parser reads the expression of a `WHERE`, a `HAVING` or an `ON`; when the parser takes a number or a string while the flag is on, add the token's text to a list, and classify the list at the end.
