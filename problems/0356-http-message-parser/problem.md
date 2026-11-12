# HTTP Message Parser

## Statement

Build `HttpParser`, the part of a web server that reads the raw bytes of an HTTP/1.1 request and works out what the request says: its method, its target, its header fields and its body. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What an HTTP request is.** When a browser or a program asks a server for something, it opens a connection and sends a request as plain text lines. Here is a complete request that sends the five bytes `hello` to the path `/notes`:

```text
POST /notes HTTP/1.1
Host: example.com
Content-Length: 5

hello
```

- The first line is the **request line**: the **method** (`POST`, what to do), the **target** (`/notes`, what to do it to) and the **version** (`HTTP/1.1`), separated by single spaces.
- Each following line is a **header field**: a name, a colon and a value. `Host` names the website, and `Content-Length` says how many bytes of body follow.
- An **empty line** ends the header section. The request line, the fields and the empty line together are the **head**.
- What follows the empty line is the **body**, if the head announced one.

On the wire every line ends with two bytes, CR (carriage return, byte 13) and LF (line feed, byte 10), together called CRLF. So the request above is this exact sequence of bytes, with CR written `\r` and LF written `\n`:

```text
POST /notes HTTP/1.1\r\nHost: example.com\r\nContent-Length: 5\r\n\r\nhello
```

The empty line is just a CRLF right after the CRLF of the last field, which is why the end of a head is always the four bytes `\r\n\r\n`.

**Why this is harder than splitting lines.** A server rarely receives a request in one piece, and it often receives several requests one after the other on the same connection. It has to find exactly where each request ends, using only what the head says. If two programs on the path of a request (a proxy and a server, say) disagree about where a request ends, the bytes one of them treats as the end of a body, the other treats as the start of a new request. The rules of HTTP/1.1, in RFC 9112, are written to remove that kind of disagreement, and this parser follows them strictly: when a message could be read two ways, it refuses it instead of guessing.

**How bytes travel in this problem.** Every method takes the bytes as a string in which each character is one byte. Every character is ASCII, with a code from 0 to 127, so the length of the string is the number of bytes. CR is the character with code 13 and LF the character with code 10; the examples and the test data are JSON, which writes them `\r` and `\n`, but your code receives the real characters, not a backslash and a letter.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, finish level 1 by about minute 35, level 2 by 65, level 3 by 90 and level 4 by 115.

## Input

- `HttpParser()`: creates a parser. It holds one connection (level 3) and its settings; the one-shot methods do not use the connection.
- `data`: bytes as described above, a string of ASCII characters.
- Each level's section describes the methods it adds and their parameters.

## Output

The methods that parse return a list of rows, each row a list of strings. A request is reported as:

- `["request", method, target, version]` first,
- then `["field", name, value]` for each header field line, in the order received,
- and, from level 2 on, `["body", content]` and then `["trailer", name, value]` for each trailer field line.

Field names are reported in lowercase; methods, targets, versions and values exactly as received. A request that cannot be parsed is reported as the single row `["error", code]`, with one of the codes that the levels define.

## Level 1: Request line and header fields

- `parseHead(data)`: parses the head at the start of `data` and returns its rows: the request row and one field row per field line. It ignores anything after the head's empty line.

**The rules**, checked in this order; the first rule that fails gives the error:

1. **Skip empty lines.** Empty lines (`\r\n`) before the request line are skipped. RFC 9112 asks servers to tolerate them, since old clients sometimes sent one after a request.
2. **Find the end.** The head ends at the first `\r\n\r\n`. If there is none, the head has not fully arrived: `incomplete`.
3. **Line endings.** Every line of the head ends with CRLF. A CR that is not followed by LF, or an LF that is not preceded by CR, anywhere in the head: `bad-line-ending`. RFC 9112 lets a recipient accept a lone LF as a line end; this parser does not, because two parsers that disagree on where a line ends disagree on everything after it. A request written with LF only therefore never shows its end, and stays `incomplete`.
4. **Request line.** It must be exactly three parts separated by single spaces: a method, a target and a version. The method is a **token**: one or more of the letters, digits and ``!#$%&'*+-.^_`|~``. The target is one or more visible characters (codes 33 to 126). The version is `HTTP/`, a digit, `.` and a digit, in upper case. Anything else: `bad-request-line`. The method is case-sensitive, so `get` is a valid method and simply not the same as `GET`.
5. **Field lines**, from top to bottom:
   - A line that starts with a space or a tab is an old way of continuing the previous field's value on a new line, called **obsolete line folding** (obs-fold). RFC 9112 lets a server reject it or replace it with spaces; this parser rejects it, including a line that starts with whitespace right after the request line: `obs-fold`.
   - Otherwise the line is a **name**, a colon and a **value**. The name is a token: no space or tab may sit between the name and the colon, and the line must have a colon. The value is everything after the first colon, with the spaces and tabs at its start and end removed (only those two characters). Inside the value, spaces, tabs and visible characters (codes 32 to 126) are allowed and kept as they are; any other control character is not. A line that breaks one of these rules: `bad-field`.
   - Field names are case-insensitive: `HOST`, `host` and `Host` are the same field. Report every name in lowercase. A name that appears on several lines gives several rows, in order.
6. **Host.** A request with version `HTTP/1.1` must have exactly one `host` field line, and a request of any version must not have more than one: `bad-host`.

### Example 1

<!-- case: ex1 -->

The first head has three fields. The value of `User-Agent` loses the spaces around it, and every name is reported in lowercase. In the second head, `HOST` is the host field, and the two `Accept-Language` lines, written in different cases, are two rows with the same name.

### Example 2

<!-- case: ex2 -->

In order: the target holds a space, so the request line has four parts (`bad-request-line`); a space sits between `Host` and the colon (`bad-field`); a line starts with spaces to continue the previous value (`obs-fold`); an `HTTP/1.1` request has no `Host` (`bad-host`); the data stops before the empty line (`incomplete`).

## Level 2: Message bodies

- `parseMessage(data)`: parses one whole request at the start of `data`: the head with the rules of level 1, then the body. It returns the request row, the field rows, the body row and any trailer rows. Bytes after the end of the request are ignored. A request that is not complete within `data`: `incomplete`.

`parseHead` does not change: it reads only the head and does not check the rules of this level.

**How long is the body?** A request says how its body is framed with one of two fields; checked in this order:

1. **`Transfer-Encoding`.** Join the values of all the `transfer-encoding` lines with commas, split the result at every comma, remove spaces and tabs around each element and drop the empty elements. The list must be exactly one element, `chunked`, compared without regard to case. Anything else is `unsupported-transfer-coding`: `gzip, chunked` names a coding this parser cannot undo, and `chunked, chunked` applies chunked twice, which RFC 9112 forbids a sender to do. The body is then chunked, as described below.
2. **`Content-Length`.** The body is exactly that many bytes after the head. At this level a case sends at most one `Content-Length` line, and its value, after the spaces and tabs around it are removed, must be one or more decimal digits (leading zeros are fine): `bad-content-length` otherwise. A sign, a space inside, a decimal point or `0x` all make it invalid.
3. **Neither.** A request with neither field has no body: report `["body", ""]`. This holds for any method, and so does the framing above: a `GET` with a `Content-Length` has a body. RFC 9112 makes the framing of a request independent of its method, so that every parser finds the same end.

**Chunked bodies** carry content whose size is not known in advance, as a series of chunks:

1. A **size line**: the chunk size in hexadecimal (digits and `a` to `f` in either case), optionally followed by spaces or tabs, a `;` and **chunk extensions**, which you ignore, then CRLF.
2. Exactly that many bytes of **chunk data**, then CRLF. The data can hold any bytes, CR and LF included. If the two bytes after the data are not CRLF: `bad-chunk`.
3. A size of zero (written `0`, or `000`) is the **last chunk**. After its size line comes the **trailer section**: zero or more field lines, each checked with the field rules of level 1 (`bad-line-ending`, `obs-fold`, `bad-field`), and then an empty line. Trailer fields describe the message after its content, such as a checksum computed while sending. The trailer lines are checked once the trailer section's empty line has arrived; until then the message is `incomplete`, even when a line that has arrived is already malformed. Report each as `["trailer", name, value]`, apart from the header fields: RFC 9112 forbids merging a trailer into the header section unless that field's definition allows it.

The body row holds the content: the chunk data joined in order, without the size lines and CRLFs. At this level every size line in a case is valid.

The checks of the head (level 1) come first, then the framing (`unsupported-transfer-coding`, `bad-content-length`), then the body as it is read, from start to end. No case at this level sends both `Transfer-Encoding` and `Content-Length`.

### Example 1

<!-- case: ex3 -->

The first request has an 11-byte body, framed by `Content-Length`. The second has neither field, so its body is empty. The third announces 11 bytes but only 5 have arrived: `incomplete`.

### Example 2

<!-- case: ex4 -->

The first body has two chunks: `5` bytes, `hello`, and `7` bytes, `, world`, then the last chunk and the empty line. The second body has one chunk and a trailer field after the last chunk, reported as a trailer row after the body.

## Level 3: Bytes in pieces

A real connection delivers bytes in pieces of any size: a request can be split anywhere, even between the CR and the LF of a line end, and one piece can hold the end of one request and the start of the next. Clients may also **pipeline**: send several requests one after the other without waiting for the answers. RFC 9112 requires the server to answer them in the order received, so the parser must report them in that order.

- `feed(data)`: appends `data` to the bytes received on the connection, and returns the rows of every request that became complete with this call, in order: each request's rows as `parseMessage` reports them, one request after the other. A request is reported by the call that delivers its last byte, never earlier and never later. Bytes that do not finish a request yet are kept for the next call.
- `close()`: the connection ends. If the bytes kept so far hold an unfinished request, return `[["error", "incomplete"]]`; otherwise `[]`. Empty lines between requests are skipped as they arrive, so they never count as unfinished, but a lone CR that might start one does.

**Errors end the connection.** When a request fails a rule, `feed` returns the rows of the requests completed before it in the same call, followed by `["error", code]`. The parser has lost track of where messages start, so it never reads that connection again: from then on, `feed` and `close` return `[]`. The same holds after `close`.

A request's errors are found at the same point as in `parseMessage`: the head's rules once its `\r\n\r\n` has arrived, a size line once its CRLF has arrived, a chunk's closing CRLF once the data and the two bytes after it have arrived, and the trailer lines once the trailer section's empty line has arrived.

`parseHead` and `parseMessage` do not change, and they never read or change the bytes the connection is holding.

### Example 1

<!-- case: ex5 -->

The first call holds two whole requests and the start of a third, so it reports the first two, one after the other. The second call completes the third. Nothing is left, so `close` reports nothing.

### Example 2

<!-- case: ex6 -->

The chunked request is split inside its chunk data and inside the line ends; it is reported by the third call, which brings the last bytes. The next request is still missing the end of its head when the connection closes: `incomplete`. After that, the connection reads nothing.

## Level 4: Ambiguity and limits

This level closes the gaps that let two parsers read the same bytes differently, and bounds what a client can make the server buffer.

**Request smuggling.** Suppose a proxy in front of a server reads a request's length one way and the server reads it another way. The bytes that the proxy took for the end of a body are, for the server, the start of a second request, one the proxy never inspected. RFC 9112 calls this request smuggling, and its defense is that every recipient frames a request the same way, refusing any request whose framing is ambiguous. The rules below are that defense.

- `setLimits(maxHeadBytes, maxBodyBytes)`: sets the largest head and the largest body this parser accepts. Before it is called there is no limit. A case calls it at most once, right after the constructor.

**New rules for the framing fields**, checked where level 2 checks the framing, in this order:

1. **Both fields.** A request with a `transfer-encoding` line and a `content-length` line, in any order and with any values: `ambiguous-length`. RFC 9112 says that `Transfer-Encoding` then overrides `Content-Length`, that such a message ought to be handled as an error because it might be an attempt at smuggling, and that a server may reject it. A parser that picks one while a parser next to it picks the other is exactly the disagreement above, so this parser rejects it.
2. **Several Content-Length values.** All the `content-length` lines are now read as one list: join their values with commas, split at every comma, remove spaces and tabs around each element and drop the empty elements. No elements, or any element that is not decimal digits: `bad-content-length`. Elements that are different numbers: `conflicting-content-length`. Elements that are the same number (such as `5, 5`, or `5` and `005` on two lines) are one length. RFC 9110 (section 8.6) allows a recipient to replace the same decimal value repeated as a comma-separated list with a single instance of it, since such a list likely comes from an upstream processor that duplicated or combined the field; this problem reads `5` and `005` as the same decimal value.
3. **Body limit.** With limits set, a `Content-Length` above `maxBodyBytes`: `body-too-large`, decided as soon as the head is parsed, before any body byte is read.

**New rules for chunk sizes:**

4. A size line is valid only as level 2 describes it: one or more hexadecimal digits, then either the end of the line, or optionally spaces or tabs followed by `;` and extensions. A sign, `0x`, a space before the digits, a space after them without `;`, an empty size, or a lone CR or LF anywhere in the line: `bad-chunk-size`.
5. With limits set, when a size line would bring the total of the chunk sizes so far above `maxBodyBytes`: `body-too-large`, decided when the size line's CRLF arrives, before the chunk's data. The body limit counts the content, not the size lines, the CRLFs or the trailers.

**New rule for the head:**

6. **Head limit.** With limits set, the head may be at most `maxHeadBytes` bytes, counting the request line, the fields and the empty line with all their CRLFs; skipped empty lines before the request line do not count. As soon as `maxHeadBytes` bytes of a head have arrived without its end among them, the request fails with `head-too-large`, even if what arrived would break another rule as well. A head of at most `maxHeadBytes` bytes is checked with the other rules once it is complete. This is checked before every other rule of the head, in `parseHead`, `parseMessage` and `feed` alike; `parseHead` checks no other limit.

**Sizes with many digits.** In level 4 cases that set limits, a `Content-Length` or a chunk size can have any number of digits, leading zeros included. RFC 9110 and RFC 9112 warn that recipients must anticipate large numerals and prevent integer overflow. A size read into a 64-bit integer can wrap around: the chunk size `10000000000000000` is 2^64, which wraps to 0 and would end the body early. Compare a size with the limit without converting more digits than an integer can hold.

### Example 1

<!-- case: ex7 -->

The first request has both framing fields: read by `Content-Length`, the body is 4 bytes; read by `Transfer-Encoding`, the body ends at the last chunk and the bytes after it start a request for `/admin`. The parser refuses it. The second has two different lengths, the third a duplicated one, which is one length. The fourth writes its chunk size with `0x`.

### Example 2

<!-- case: ex8 -->

The limits are a 64-byte head and a 10-byte body. An 11-byte body fails before it is read, and a 10-byte one passes. A head with a long cookie is over 64 bytes. On the connection, 75 bytes of a head with no end in sight fail at once: the parser does not wait for more.

## Constraints

- At most 2,000 calls per test, and at most 10,000 bytes per call.
- Every character of `data` has a code from 0 to 127.
- A `Content-Length` or a chunk size has at most 7 digits, except in level 4 cases that set limits.
- `16 <= maxHeadBytes <= 1,000,000` and `0 <= maxBodyBytes <= 1,000,000`.

## Follow-ups

- This parser bounds the head and the content. A client can still send a chunk size line, or a trailer section, that never ends. How would you bound those, and what should each limit be relative to the others?
- RFC 9112 says a server must treat the framing of an HTTP/1.0 request that carries `Transfer-Encoding` as faulty. Why is an HTTP/1.0 message with `Transfer-Encoding` suspect in the first place?
- Responses are framed differently from requests: a response to `HEAD` never has a body whatever its fields say, and a response without either framing field ends when the connection closes. Which of your functions would need to know the request a response answers?
- `feed` searches the kept bytes for `\r\n\r\n` from the start each time. With a head arriving one byte per call, that is quadratic. How would you remember where the last search stopped?

## Hints

### Hint 1

Work on one request at a time and in stages: skip empty lines, find the end of the head, check the head's lines in the stated order, then read the body. Write the head stage first and test it with `parseHead` before you touch bodies. In most languages, splitting the head text on `"\r\n"` gives you its lines, and the first line is the request line.

### Hint 2

For a field line, look for the first colon. The name is everything before it, and it must be a non-empty token; a space before the colon makes the name invalid without any special case. Trim only spaces and tabs from the value; a general-purpose trim function may remove other characters too.

### Hint 3

A chunked body is a small loop: read a line up to CRLF, turn the hexadecimal size into a number, stop at zero, otherwise take exactly that many bytes and check that CRLF follows. Do not search for the next CRLF to find the end of the data: the data may contain CRLF itself.

### Hint 4

For the connection, keep a buffer of unread bytes. Write each stage so that it can say "not enough bytes yet" instead of failing, and have `feed` run the stages again from the start of the buffer each time, removing a request's bytes from the buffer once it is reported. Then the order in which bytes arrive cannot change the result, only the call that reports it.

### Hint 5

To decide `head-too-large` without waiting, search for `\r\n\r\n` only within the first `maxHeadBytes` bytes of the head. If it is not there and that many bytes have arrived, the head cannot fit, whatever comes next.

### Hint 6

For a size with many digits, remove the leading zeros first. A number with more significant digits than the limit has is larger than the limit, so you only ever convert a short string into an integer.
