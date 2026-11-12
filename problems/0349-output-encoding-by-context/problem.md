# Output Encoding by Context

## Statement

A web page is built from text that your server writes, and some of that text came from somewhere you do not control: a user's display name, a search term, a product review. Write `encodeOutput`, which takes such untrusted text and the **context** it is about to be written into, and returns the text encoded so that a browser reads it as plain data in that context and never as part of the page's structure or code.

**What goes wrong without it.** A browser does not know which parts of a page came from you and which came from a user. Suppose a profile page writes a display name between two tags, `<p>Hello, NAME</p>`. A user who picks a name containing `<` has started a new tag in your page, and whatever markup or script follows is now yours as far as the browser can tell. This is **cross-site scripting** (XSS): untrusted text ends up being parsed as markup or code in someone else's page, where it runs with that page's privileges, such as reading what the page shows. The defense this problem practices is **output encoding**: just before writing the text, replace each character that has a special meaning *in that spot* with a form the browser shows as the character itself. In HTML text, `<` becomes `&lt;`, which the browser displays as `<` but never treats as the start of a tag.

**The context decides the encoding.** A page is read by more than one parser. The HTML parser reads tags and attributes, the URL parser reads links, and the JavaScript engine reads scripts, and each of them has different special characters. Encoding meant for one context can leave another context's special characters untouched:

- HTML encoding leaves a backslash and a line break alone. Inside a JavaScript string, a backslash just before the closing quote escapes that quote, so the string does not end where you meant and the text after it is read as code. A raw line break is a syntax error that stops the whole script.
- HTML encoding turns `&` into `&amp;` but leaves `#`, `=` and `+` alone. In a URL query value, `&` still starts a new parameter, `#` ends the query, and the usual form decoding of a query reads `+` as a space, so one value turns into several, or loses its end.
- Every encoding below assumes the value sits between quotes. Written into an attribute *without* quotes, even correctly encoded text can end the value at a plain space, and what follows becomes a new attribute.

So an encoder takes the context as input, and a context it does not know is refused rather than guessed.

**The four contexts.** `context` names where the text will go:

| `context` | Where the text goes | Example spot, with `X` for the text |
|-----------|---------------------|-------------------------------------|
| `html-text` | Between tags, as text | `<p>X</p>` |
| `html-attribute` | Inside an attribute value in double quotes | `<input value="X">` |
| `url-query` | One value in a URL's query string | `/search?q=X` |
| `js-string` | Inside a JavaScript string literal, in a `<script>` element | `<script>let name = "X";</script>` |

The rules, exactly:

- `html-text` and `html-attribute`: replace each of these five characters with its entity, and leave every other character as it is.

  | Character | Becomes |
  |-----------|---------|
  | `&` | `&amp;` |
  | `<` | `&lt;` |
  | `>` | `&gt;` |
  | `"` | `&quot;` |
  | `'` | `&#x27;` |

  The two contexts share one rule on purpose. Between tags, `<` would start a tag and `&` a character reference. Inside a quoted attribute, the matching quote would end the value and `&` would again start a reference. Encoding all five covers both places, for an attribute in either kind of quote.
- `url-query`: write the text as UTF-8 bytes. Each byte that is an ASCII letter, an ASCII digit, `-`, `.`, `_` or `~` stays as that character. Every other byte becomes `%` followed by its value as two **uppercase** hexadecimal digits. A space is `%20` (not `+`), `é` (bytes `C3 A9`) is `%C3%A9`.
- `js-string`: each ASCII letter and ASCII digit stays. Every other character becomes `\u` followed by four **uppercase** hexadecimal digits of its UTF-16 code unit. A character outside the Basic Multilingual Plane, such as most emoji, is two UTF-16 code units (a *surrogate pair*) and becomes two escapes: `😀` (U+1F600) is `\uD83D\uDE00`. Escaping everything except letters and digits is a deny-by-default rule: it covers both kinds of quote, the backslash, every line break, and the `<` that would let the HTML parser end the script early (in `</script`) or change how it reads the script (in `<!--`).
- Any other `context`, including a different spelling or case of these four names: return `""`. Writing the text unencoded would be the unsafe default.

## Input

- `text`: the untrusted text, any Unicode text.
- `context`: one of `html-text`, `html-attribute`, `url-query`, `js-string`, or any other string, which is refused.

## Output

The encoded text, or `""` for a context that is not one of the four.

## Examples

### Example 1

<!-- case: ex1 -->

Between tags, `&`, `<` and the double quotes are replaced. `Jerry`, the digits and the spaces are ordinary text and stay.

### Example 2

<!-- case: ex2 -->

In a quoted attribute the same five characters are replaced, so the double quotes can no longer end the value. `é` has no special meaning in HTML and stays.

### Example 3

<!-- case: ex3 -->

In a query value, every byte that is not unreserved is encoded: each space becomes `%20`, `&` becomes `%26`, `/` becomes `%2F` and `?` becomes `%3F`. Left as it is, the `&` would split the value into two parameters.

### Example 4

<!-- case: ex4 -->

In a JavaScript string, the space, the line break and both double quotes become `\u0020`, `\u000A` and `\u0022`. The letters and digits stay.

### Example 5

<!-- case: ex5 -->

`css` is not one of the four contexts, so nothing is written. (CSS has encoding rules of its own.)

## Constraints

- `0 <= text.length <= 1000`, counted in UTF-16 code units.
- `text` is well-formed Unicode: no unpaired surrogate code units, and no U+0000.
- `context` has at most 20 characters.

## Follow-ups

- A link's `href` holds a whole URL, not a query value. Why is encoding the whole URL with the `url-query` rule wrong, and what must be checked about a URL that a user supplied before it goes into `href`?
- A value written into an event handler attribute (`onclick="..."`) is read by the HTML parser first and by JavaScript second. In which order would you apply two of these encoders, and why does attribute encoding alone not protect it?
- Templating libraries encode by default. Which of the four contexts does a typical HTML template encode for, and where in a template would that default still be wrong?

## Hints

### Hint 1

Start with the easiest context, `html-text`. Go through the text one character at a time and, for each character, decide what to write: either the character itself or its replacement from the table. A small lookup table from character to replacement keeps the decision in one place.

### Hint 2

Check the context first and pick an encoder for it. Two contexts share an encoder. Anything that is not exactly one of the four names gets `""`, so make that the outcome when the lookup finds nothing.

### Hint 3

For `url-query`, turn the text into UTF-8 bytes first and work byte by byte: a character such as `é` or `東` is several bytes, and each byte gets its own `%HH`. Check which characters your language's built-in URL encoder leaves alone; the rule here may encode more than it does.

### Hint 4

For `js-string`, decide "letter or digit" with an explicit ASCII test, since your language's own "is alphanumeric" test may accept letters and digits of other scripts. The escape is per UTF-16 code unit: a TypeScript string already indexes code units, while a Python string holds code points, so a character above U+FFFF has to be split into its two surrogates (encoding the text as UTF-16 does it for you). Format the number as four uppercase hex digits, padded with zeros.
