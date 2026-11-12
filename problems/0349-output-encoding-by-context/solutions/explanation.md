# Output Encoding by Context: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| encoder-per-context | optimal | O(n) | O(n) | default answer |

`n` is the length of `text`.

## Approach: encoder-per-context (One encoder per context chosen by name with a refusal for any other name)

### Intuition

Each context is read by a different parser, and each parser has its own short list of characters that change its state: the HTML tokenizer reacts to `<` and `&` in text and to the closing quote and `&` inside an attribute value, a URL parser to `&`, `=`, `#` and friends, and a JavaScript engine to quotes, backslashes and line breaks. An encoder is a function from text to text that leaves no such character in a form the parser would act on. So the design is a table from context name to encoder, and the one decision that matters for safety is what happens when the name is not in the table: refuse, never fall through to "write it as it is".

The rules are not equally strict, and that is deliberate. HTML contexts use a short deny-list of five characters, the one that the OWASP cheat sheet gives for HTML, because everything else is shown as text. The URL rule is an allow-list of the unreserved characters of RFC 3986. The JavaScript rule is the strictest allow-list, letters and digits only, because a JavaScript string inside a `<script>` element is read by two parsers, one after the other, and the HTML parser runs first: it ends the element at `</script` wherever that appears, even inside a string.

### Algorithm

1. Look up `context` in a table of four entries. `html-text` and `html-attribute` map to the same encoder. A missing entry returns `""`.
2. HTML encoder: for each character, write its entity if it is one of `& < > " '`, else the character.
3. URL query encoder: encode the text as UTF-8; for each byte, write the character if the byte is an ASCII letter, digit, `-`, `.`, `_` or `~`, else `%` and the byte as two uppercase hex digits.
4. JavaScript string encoder: for each UTF-16 code unit, write the character if it is an ASCII letter or digit, else `\u` and the unit as four uppercase hex digits.

### Correctness

HTML: the tokenizer's data state switches state only on `&` (a character reference) and `<` (a tag), and the double-quoted attribute value state only on `"` (end of value) and `&`; the single-quoted state does the same with `'`. After encoding, none of these characters is left in the output except the `&` that starts one of our own five entities, each of which decodes back to exactly the character it replaced. So the parser stays in the state it was in and shows the original text.

URL: the output holds only unreserved characters and `%HH` triples. Unreserved characters have no delimiting role in any URL component, and a `%` in the output always starts a triple we wrote, so the decoder recovers exactly the UTF-8 bytes of the text, and nothing in the value can end the query or start a new parameter.

JavaScript: the output holds only ASCII letters, digits, backslashes and the letter `u`, and each backslash starts a `\uXXXX` escape. None of these ends a string literal in either quote, none is a line terminator, and none is `<`, so the HTML parser sees neither `</script` nor `<!--` in it. Each escape stands for one UTF-16 code unit, so a surrogate pair of escapes rebuilds a character above U+FFFF.

Refusal: every name outside the table returns `""`, which is safe in any context.

### Complexity

- Time: O(n) — each character, byte or code unit is visited once, and one input character produces at most 12 output characters (a 4-byte UTF-8 character is `%HH` four times).
- Space: O(n) — the output.

### Trade-offs

- A deny-list for HTML keeps the output readable (`café` stays `café`) and is what Python's `html.escape` produces. An allow-list that turned every non-alphanumeric character into a numeric reference would also be safe, and much harder to read.
- The JavaScript rule escapes far more than one quote style strictly needs. A narrower rule (escape `"`, `\`, the line terminators and `<`) can work for a double-quoted string inside a script, but it depends on the quote style and on remembering every line terminator. Letters and digits only has no such conditions, at the cost of longer output.
- Passing data to a script through an HTML attribute or a JSON block that the script reads and parses avoids building JavaScript source from data altogether, and is often better than encoding into a string literal.
- In production code, use your framework's encoding or a maintained encoder whose documented contract names the exact context, as the cheat sheet advises; it also warns against hand-made quote escaping and generic hex rules. Writing one here is for seeing why each character matters, and the contract of this one is narrow: a value inside a quoted string literal, inside a `<script>` element, never passed on to `eval` or another sink that runs code.
- The cheat sheet suggests `encodeURIComponent` for query values built in JavaScript, followed by attribute encoding when the URL goes into an attribute. The `url-query` rule here uses the stricter unreserved set of RFC 3986, so its output also contains no quote of either kind.

### Pitfalls and edge cases

- **Falling through on an unknown context.** `HTML-TEXT`, `html`, `html-attr` and `""` are refused (`h24` to `h27`). A default branch that returns the text unchanged would write untrusted text raw.
- **Skipping "already encoded" text.** Encoding is not idempotent and must not try to be: the text `&amp;` is five characters chosen by a user, and is written as `&amp;amp;` (`h1`). An encoder that leaves existing entities alone lets the user write any entity they like.
- **Attributes and elements read twice.** The HTML rule is right for `title` or `value`, not for `href`, `src`, `on*`, `style` or `srcdoc`, whose values a second parser reads after the entities are decoded, and not for the content of `<script>` or `<style>`, where entities are not decoded at all. A URL from a user needs its scheme checked against an allow-list before it goes into `href`; no encoding does that.
- **Forgetting `>` or `'`.** `h3` and `h5` need both; `'` becomes `&#x27;`, as in the cheat sheet's table.
- **Built-in URL encoders.** JavaScript's `encodeURIComponent` leaves `! ' ( ) *` unencoded, following the older RFC 2396 list (`h8`). Python's `quote` keeps `/` by default (`h11`), and `quote_plus` writes a space as `+` (`h9`). Only the exact rule passes every case.
- **Encoding characters instead of bytes.** `é` is `%C3%A9`, not `%E9`, and an emoji is four bytes (`h10`).
- **A lone `%`.** It must become `%25`, or a decoder reads `%41` in the text as `A` (`h12`).
- **Unicode "alphanumerics".** Python's `str.isalnum()` is true for `é`, `²` and `٣`, which must be escaped (`h21`). The test must be ASCII.
- **Characters above U+FFFF in JavaScript.** One emoji is two escapes, `\uD83D\uDE00`; a single `\U0001F600` or `\u{1F600}` does not follow the rule (`h19`).
- **Lowercase hex.** `\u00e9` or `%c3` decode the same but do not match the stated output (`h19`, `h10`).
- **Line separators.** U+2028 and U+2029 have been allowed inside string literals since ECMAScript 2019 (the 2018 edition's grammar does not allow them), but older engines treat them as line breaks; carriage return and line feed are never allowed (`h18`).
- **Template literals.** `${` starts a substitution in a backtick string. Escaping `$` and `{` keeps even that case inert (`h22`), though this problem's context is an ordinary quoted string.

### Language notes

- Python: `html.escape(text)` with its default `quote=True` produces exactly the five replacements of the HTML rule. `text.encode("utf-8")` gives the bytes for the URL rule, and `text.encode("utf-16-be")` gives the code units for the JavaScript rule two bytes at a time, splitting characters above U+FFFF into surrogates for you. `f"{value:02X}"` and `f"{value:04X}"` format uppercase hex.
- TypeScript: a `for...of` loop walks code points, which suits the HTML rule, while indexing (`text[i]`, `charCodeAt(i)`) walks UTF-16 code units, which is what the JavaScript rule needs. `new TextEncoder().encode(text)` gives UTF-8 bytes. `toString(16).toUpperCase().padStart(n, "0")` formats the hex. A `Map` keeps the entity table and the encoder table free of inherited keys.

## Further reading

- [OWASP Cross Site Scripting Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html): output encoding per context, the five HTML entity replacements, always quoting attributes, why attribute encoding does not protect URL, event-handler, style or srcdoc attributes, encoding URL parameter values rather than whole URLs, and why JavaScript contexts need an encoder that also accounts for the enclosing script.
- [HTML Standard, 13.2.5 Tokenization](https://html.spec.whatwg.org/multipage/parsing.html#tokenization): the data state, the attribute value states (double-quoted, single-quoted and unquoted) and the characters each one reacts to.
- [HTML Standard, 4.12.1.3 Restrictions for contents of script elements](https://html.spec.whatwg.org/multipage/scripting.html#restrictions-for-contents-of-script-elements): why `</script` and `<!--` inside a script's strings are dangerous, and the advice to escape them.
- [RFC 3986, Uniform Resource Identifier (URI): Generic Syntax](https://www.rfc-editor.org/rfc/rfc3986), sections 2.1 (percent-encoding, uppercase hex), 2.3 (unreserved characters), 2.5 (UTF-8 for text) and 3.4 (the query ends at `#`).
- [URL Standard, application/x-www-form-urlencoded parsing](https://url.spec.whatwg.org/#urlencoded-parsing): a query is split on `&` and `+` is read as a space.
- [ECMAScript Language Specification, String Literals](https://tc39.es/ecma262/multipage/ecmascript-language-lexical-grammar.html#sec-literals-string-literals): which characters may appear in a string literal, and the `\uXXXX` escape of one UTF-16 code unit.
- [ECMAScript 2019 Language Specification](https://262.ecma-international.org/10.0/), the edition whose string literal grammar first lists `<LS>` and `<PS>` as string characters, and the [TC39 list of finished proposals](https://github.com/tc39/proposals/blob/main/finished-proposals.md), where the JSON superset proposal is dated 2019.
- [ECMAScript Language Specification, encodeURIComponent](https://tc39.es/ecma262/multipage/global-object.html#sec-encodeuricomponent-uricomponent): the characters it leaves unescaped.
