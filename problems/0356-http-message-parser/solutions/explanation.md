# HTTP Message Parser: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| framing-state-machine | optimal | O(n) per message of n bytes; O(k) per feed call, k the bytes kept | O(k) for the bytes kept | default answer; the same stages serve the one-shot methods and the connection |

Here `n` is the number of bytes of one request and `k` the number of bytes the connection holds that are not yet part of a reported request.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Parse a head | none: a function from bytes to rows |
| 2 | Frame the body | none: the head's fields decide the body, read by length or by chunks |
| 3 | Bytes in pieces | a buffer of unread bytes and a closed flag; every stage can say "not enough bytes yet" |
| 4 | Ambiguity and limits | two optional limits; the framing checks refuse what two parsers could read differently |

The decision that makes level 3 small is to write levels 1 and 2 as stages that can stop and report "need more bytes" instead of failing. The connection is then a loop that runs the same stages over its buffer, so pipelining and arbitrary splits need no new parsing code.

## Approach: framing-state-machine (Staged parse over a buffer that resumes when more bytes arrive)

### Intuition

A request is a head and a body, and only the head can say how long the body is. So the parser works in stages, each of which only looks at bytes that the previous stage has delimited: skip empty lines, find the `\r\n\r\n` that ends the head, check the head's lines, decide the framing from its fields, then read exactly the body that the framing announces. A stage that runs out of bytes does not fail: it reports that it needs more, and nothing is reported or consumed. That one rule makes the parser independent of how the bytes are split: whatever the split, the stages see the same bytes in the end, and only the call that completes a request differs.

Being strict is the other half. Every place where the rules leave a choice (a lone LF, a folded line, a space before a colon, a body framed two ways, a list of lengths that disagree) is a place where two parsers on the same path could disagree on where a request ends. Request smuggling lives in those disagreements, so the parser refuses each of them with an error code instead of picking a reading.

### Algorithm

1. **Skip empty lines** at the start of a request: while the next two bytes are `\r\n`, move past them.
2. **End of the head.** Search for `\r\n\r\n`. Without a head limit, if it is not there, need more bytes. With a limit, search only the first `maxHeadBytes` bytes; if it is not there and that many bytes have arrived, fail with `head-too-large`, otherwise need more.
3. **Check the head**, in order: any CR or LF that is not part of a CRLF (`bad-line-ending`); split the rest on CRLF; the request line splits on single spaces into exactly a token, a target of visible characters and `HTTP/d.d` (`bad-request-line`); each field line is not folded (`obs-fold`), has a token name directly followed by a colon, and a value that, trimmed of spaces and tabs, holds only tabs and visible characters (`bad-field`); then the number of `host` lines (`bad-host`). Names are lowercased in the rows. `parseHead` stops here.
4. **Framing.** Collect the values of the `transfer-encoding` and `content-length` lines. Both present: `ambiguous-length`. Transfer-Encoding: the comma-separated list over all its lines, with empty elements dropped, must be exactly `chunked` in any case (`unsupported-transfer-coding`). Content-Length: the same kind of list must be non-empty, all digits (`bad-content-length`) and one number (`conflicting-content-length`); with a body limit, that number must not exceed it (`body-too-large`). Neither field: an empty body.
5. **Body by length.** If fewer bytes than the length are available, need more; otherwise the body is the next `length` bytes.
6. **Body by chunks.** Repeat: find the CRLF that ends the size line (need more if missing); the line is hex digits, then optionally spaces or tabs, `;` and anything without CR or LF (`bad-chunk-size`); with a body limit, the running total plus this size must not exceed it (`body-too-large`); a size of zero ends the loop; otherwise need the data and two more bytes, which must be CRLF (`bad-chunk`). After the last chunk, an immediate CRLF ends the message; otherwise the trailer section runs to the next `\r\n\r\n` (need more if missing) and its lines are checked like field lines.
7. **The connection.** `feed` appends to the buffer and loops: skip empty lines and drop them, run steps 2 to 6 on the buffer, and on success report the rows and drop the request's bytes. On "need more", return what was reported so far. On an error, return it after the rows of this call and mark the connection closed. `close` reports `incomplete` when the buffer is not empty. Both return nothing once the connection is closed.

### Correctness

Each stage consumes bytes only after it has seen everything it needs, so a stage that needs more bytes leaves the buffer as it was. By induction on the calls, after any call the buffer holds exactly the bytes received after the last reported request and the skipped empty lines, which is what a fresh parse of the remaining bytes would start from. A request is therefore reported by the first call after which its last byte is available: earlier, a stage would still need bytes; later, the loop would already have run on it. The same argument covers errors, with one subtlety: each check is phrased in terms of bytes that have already arrived (the head once its end is in, a size line once its CRLF is in, the limit once `maxHeadBytes` bytes are in), so the call that reports an error does not depend on how the earlier bytes were split.

The head limit decision is exact: if the end of the head is within the first `maxHeadBytes` bytes, the head is at most that long; if it is not, and `maxHeadBytes` bytes have arrived, any end that arrives later makes the head at least one byte longer than the limit.

Refusing ambiguity is what makes framing unique. A message accepted by this parser has at most one framing field, a Transfer-Encoding that is exactly `chunked`, or Content-Length values that are all the same number, so there is only one length any reader following the RFC could compute, and the parser computes it without integer overflow.

### Complexity

- Time: O(n) per message of n bytes; O(k) per feed call, k the bytes kept — each byte of a request is checked a constant number of times once its stage runs; a call that does not finish a request searches the kept bytes again for the end of the head, which is linear in what is kept.
- Space: O(k) for the bytes kept — the buffer holds the unfinished request; reported requests are dropped from it, and the limits of level 4 are what bound it.

### Trade-offs

- Re-running the stages from the start of the buffer on every call is simple and obviously split-independent. A parser that remembers how far it got (the offset where the `\r\n\r\n` search stopped, the chunk it is in) avoids rescanning and makes a request that arrives one byte per call linear instead of quadratic. Production parsers do that; the bookkeeping is where their bugs live.
- Parsing on characters works here because every byte is ASCII. A real server parses bytes: RFC 9112 warns that decoding a message as Unicode text first creates vulnerabilities, because decoders handle invalid sequences that contain an LF in different ways.
- Strictness costs compatibility. Accepting a lone LF or folded lines, as RFC 9112 allows a recipient to, helps old clients, and a single server may choose it. A server behind a proxy, or a proxy in front of servers, should be strict, because the danger is in two readers disagreeing.
- Errors as data (`["error", code]`) rather than exceptions keep the connection's "rows so far, then the error" result simple, and match what a server does: answer `400 Bad Request` and close.

### Pitfalls and edge cases

- Level 1, splitting on any whitespace. `GET  /` with two spaces, a tab between parts, or a trailing space are invalid request lines. `str.split()` with no argument, or a regular expression with `\s+`, accepts them (`h1`). The version is case-sensitive and has exactly one digit on each side of the point; `get` is a valid method.
- Level 1, trimming too much or too little. Only spaces and tabs around a value are optional whitespace; a vertical tab or form feed is a control character, and a general `trim` that removes it hides a `bad-field` (`h2`). Inner spaces and tabs stay. A value can be empty, and a value can contain colons: split on the first colon only.
- Level 1, whitespace before the colon. RFC 9112 requires a server to reject it, because parsers that strip it and parsers that keep it see different field names (`h2`, `ex2`).
- Level 1, line endings. A lone CR inside a value, a lone LF between fields, or `\r\r\n` are all `bad-line-ending` (`h3`). A head written with LF only has no `\r\n\r\n` at all and stays `incomplete`.
- Level 1, folding. A line starting with a space or a tab is `obs-fold`, even right after the request line, where RFC 9112 calls it whitespace between the start line and the first field (`h4`). Joining it to the previous value is allowed for a single server by the RFC but changes the field for anyone who does not.
- Level 1, Host. Exactly one for HTTP/1.1, at most one for any version, matched without case (`h5`). The rule is checked after every field line, so a bad field line wins over a missing host (`h6`).
- Level 2, Content-Length leniency. Integer parsers accept `+5`, ` 5` or `5_000` in some languages; the field is digits only (`h11`). Leading zeros are fine.
- Level 2, chunk sizes are hexadecimal: `A` is 10 and `1a` is 26, and an extension after `;` is ignored, as are spaces or tabs before the `;` (`h9`). Data may contain `\r\n` and digits, so the end of a chunk is found by counting, not by searching (`h9`). The two bytes after the data must be CRLF (`h12`).
- Level 2, trailers are not headers. They are reported after the body with their own tag, even when a trailer has the name of a header field (`h12`), and they follow the field rules.
- Level 2, Transfer-Encoding. `Chunked` and `CHUNKED` are chunked; `gzip, chunked`, `chunked, gzip`, `identity` and `chunked` on two lines are not (`h10`). Checking only the last element accepts a coding the parser cannot undo.
- Level 3, one request per call. A call can complete several pipelined requests, and all of them are reported in order (`h14`, `ex5`). Splits can fall between CR and LF of any line end, inside `\r\n\r\n`, inside a size line and between chunk data and its CRLF (`h13`, `h20`).
- Level 3, after an error. The rows of requests completed earlier in the same call come first, then the error (`h15`, `h22`). Nothing after it is ever parsed: a server that resynchronizes on the next request line is reading bytes it can no longer trust.
- Level 3, close. A partial head, a partial body and a lone CR are all unfinished (`h17`, `h18`); skipped empty lines are not (`h19`). `parseMessage` and `parseHead` must not share the connection's buffer (`h21`).
- Level 4, picking a framing. Letting Transfer-Encoding win, as RFC 9112 describes for a recipient that processes such a message, or letting Content-Length win, both accept the request of `ex7` and `h23`. Refusing both framings together is the safe choice, whatever the order or case of the fields.
- Level 4, Content-Length lists. Equal numbers are one length, including `5, 005` and two lines of `5`; different numbers conflict; an empty or non-numeric element is invalid (`h24`). Taking the first value is the smuggling bug again.
- Level 4, lenient size parsing. Converters that accept `0x5`, `+5` or surrounding spaces turn invalid size lines into sizes (`h25`).
- Level 4, overflow. `10000000000000000` in hexadecimal is 2^64; in a 64-bit unsigned integer it wraps to 0, which ends the body and turns the rest into a new request. `18446744073709551621` wraps to 5 (`h26`). Count significant digits after removing leading zeros: a size padded with zeros is still small.
- Level 4, when to fail. The head limit fails as soon as the limit is reached without the end, not when the head finally arrives (`h28`); a head of exactly the limit is fine (`h27`, `h29`). The body limit fails as soon as the length or a size line is known, before the bytes arrive (`h30`, `h31`), and counts the total of the chunks, not each chunk (`h30`).

### Language notes

- Python: `str.find(sub, start, end)` searches a window, which is the head limit in one call. `str.strip(" \t")` trims only the two optional-whitespace characters, where `str.strip()` trims every Unicode whitespace. Python integers do not overflow, so `int(digits, 16)` is safe here; it also accepts `0x`, `+`, `_` and surrounding spaces, which is why the size is checked against the hex digits first.
- TypeScript: `indexOf` has a start but no end, so the head limit searches `slice(start, start + limit)`. `parseInt` stops at the first invalid character and `Number("")` is 0, so both need the digit check first. A `number` holds integers exactly only up to 2^53, so a size with more than 12 significant digits is treated as over any limit without converting it.
- Java: `String.indexOf` and `substring` work on UTF-16 units, which are bytes here because every character is ASCII. `Long.parseLong(s, 16)` throws on overflow rather than wrapping, but it also accepts a leading `+` or `-`; the digit check comes first, and sizes with more than 12 significant digits are treated as over any limit without parsing.
- Kotlin: `String.trim(' ', '\t')` trims the chosen characters; `toLongOrNull(16)` accepts a sign, so the digits are checked first, as in Java.
- Go: strings are byte sequences, so `len` and indexing count bytes. `strings.Index` and `strings.HasPrefix` do the searching, and `strings.Trim(s, " \t")` trims only spaces and tabs. `strconv.ParseInt` reports overflow as an error instead of wrapping; the reference also counts significant digits first, so it only ever converts short strings.
- Rust: `str::find` and slicing work in byte offsets, which never split a character here because the input is ASCII. `u64::from_str_radix` accepts a leading `+`, so the digits are checked first; it reports overflow as an error, and the reference counts significant digits before parsing.

## Further reading

- [RFC 9112, HTTP/1.1](https://www.rfc-editor.org/rfc/rfc9112.html): message format and parsing, including empty lines before the request line, the lone LF and bare CR rules, and whitespace after the start line (section 2.2); the request line and its single spaces (section 3); field line parsing and the rule against whitespace before the colon (section 5.1); obsolete line folding (section 5.2); Transfer-Encoding, including that a server may reject a request with both framing fields and that an HTTP/1.0 message with Transfer-Encoding has faulty framing (section 6.1); the message body length rules in order of precedence, including Content-Length lists (section 6.3); chunked coding, extensions, trailers and the warning about large hexadecimal numerals (section 7.1); incomplete messages (section 8); pipelining (section 9.3.2); request smuggling (section 11.2).
- [RFC 9110, HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html): case-insensitive field names (section 5.1); combined field values (section 5.2); field limits and why ignoring oversized fields helps smuggling (section 5.4); field value characters, and CR, LF and NUL as invalid and dangerous (section 5.5); lists and empty elements (section 5.6.1); tokens (section 5.6.2); optional whitespace (section 5.6.3); trailer fields (section 6.5); Content-Length, repeated values and large numerals (section 8.6).
