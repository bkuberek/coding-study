# Secure File Upload (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per upload | per upload | default answer: count the body as it arrives, key storage by an id the service made, trust only the bytes, and serve only what the scanner cleared |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Upload within a size limit and a quota, store under a generated key, serve, delete | `readBody` in `src/http.ts`, `displayName` in `src/names.ts`, `FileStore` with `reserve` in `src/store.ts`, `Uploads.receive` in `src/uploads.ts` |
| 2 | Decide the type from the bytes, refuse polyglots, serve with safe headers | `sniff` and `hasActiveContent` in `src/sniffing.ts`, the extension check in `receive`, `servingHeaders` in `src/serving.ts` |
| 3 | Quarantine, scan with retries, fail closed, scan again later | `scan` in `src/scanner.ts`, `Quarantine` in `src/quarantine.ts`, the quarantine and release folders of `FileStore` |
| 4 | Signed links that expire | `linkTo` and `checkLink` in `src/links.ts`, and the `/shared/{id}` route |

## Approach: reference (Count the body as it arrives, trust only the bytes, and serve only what the scanner cleared)

### Intuition

An upload is a stranger handing you a box with a label on it. Everything on the label is the stranger's handwriting: how big the box is, what is inside, what to call it. The whole problem is learning which parts of the label to ignore, and when to stop accepting the box at all.

The size on the label is a promise, so check it before you open anything, and then count what actually arrives, because the stranger can keep pushing more in or simply stop halfway. Reading the whole body and then measuring it means the stranger decides how much memory you spend and how long you wait.

The name on the label is for people, never for your filesystem. A name like `../alice/avatar.png` is a path to someone else's file, and even an innocent `avatar.png` collides with the next user's. So the service makes its own key, a random id, and keeps the name only as metadata.

The type on the label is a hope. The bytes say what a file is, and even the bytes can be two things at once: a GIF that is also a page, a PDF that runs script. So the service sniffs the magic number, refuses what holds markup, and then tells the browser exactly what it is serving and forbids it to guess.

Last, the contents might be hostile in a way only a scanner can see. Until the scanner says "clean", the file waits in quarantine. When the scanner is slow, down or confused, the answer is not "probably fine": the file stays where it is.

### Say it out loud

"I treat every part of an upload as untrusted input. First I check who is asking, before reading anything. Then the size: I refuse a declared `Content-Length` over the limit straight away, and otherwise I count bytes as they stream in and stop the moment they pass it, because a chunked body has no length and a client can send forever or stall.

"The file's name is metadata only. I keep the last path segment for display and the download header, and I store the bytes under a random 128-bit id, so there is no way for a name to become a path or to overwrite another file. Quota is checked and reserved in one synchronous step, so concurrent uploads can't both squeeze into the same room.

"I decide the type from the magic bytes, never from the client's content type or the extension, and the extension must agree with what the bytes are. I refuse files that also contain HTML or a PDF's script. When I serve, I set the type I sniffed, `nosniff`, and `attachment` for anything I would not show inline.

"Every file sits in quarantine until the scanner says clean. I give each request a timeout, retry timeouts, 429s and 5xx with backoff, honoring `Retry-After`, and anything that is not a clear verdict leaves the file pending. Pending is never served. That's failing closed. A pending file can be scanned again later.

"For sharing, I sign the file id and an expiry with an HMAC, so the link can't be extended or moved to another file, and I compare signatures in constant time."

### Algorithm

1. Check `X-User`, then the declared `Content-Length`. Read the body chunk by chunk, counting, and refuse it as soon as the count passes `MAX_BODY_BYTES`.
2. Parse the JSON, decode strict base64, and reduce the name to what follows its last `/` or `\`, refusing what cannot be shown.
3. Sniff the type from the first bytes; refuse anything else, a name whose extension disagrees, and a file that holds markup or a PDF's script.
4. Check the quota and record the file as pending in one synchronous step, with a new random id.
5. Write the bytes to quarantine under the id. Scan: up to 3 attempts of 1 s each, waiting 250 ms, then 500 ms, or `Retry-After` after a 429. A clean verdict moves the bytes out of quarantine; an infected one deletes everything; no verdict leaves the file pending.
6. Serve only a clean file, with its sniffed type, `nosniff` and a `Content-Disposition` by type.
7. A link signs `<id>.<expires>` with HMAC-SHA256. Opening one checks the signature in constant time, then the expiry, then the file.

### Design

- `src/server.ts`: the routes, `X-User` before any body, link creation and opening, and the starter's 2 s limit on receiving a request, kept as a second line against a client that stalls.
- `src/config.ts`: what the service reads from its environment.
- `src/limits.ts`: every number the statement sets, in one place.
- `src/http.ts`: `readBody`, which refuses a body from its declared length or its running count, and `send`.
- `src/names.ts`: `displayName`, the name as metadata, and `extensionOf`.
- `src/sniffing.ts`: `sniff`, the allowed types by magic number, and `hasActiveContent`.
- `src/store.ts`: `FileStore`, which keeps records and bytes under the data directory in `records/`, `quarantine/` and `files/`, all keyed by id, with `reserve` taking quota synchronously.
- `src/scanner.ts`: `scan`, the attempts, timeouts and waits, and the rule that only a verdict decides.
- `src/quarantine.ts`: `Quarantine`, which applies a verdict to a stored file and runs one rescan per file at a time.
- `src/uploads.ts`: `Uploads.receive`, the checks in the statement's order.
- `src/serving.ts`: the serving headers, and the refusals for pending and infected files.
- `src/links.ts`: signing and checking links.

Not graded, and worth discussing:

- **A domain for user content.** Serving uploads from a separate domain, with no cookies and nothing else on it, means that even a file that slips through runs as nobody. `Content-Security-Policy: sandbox` on the response is a second layer.
- **Streaming to storage.** With real limits in megabytes, the body would go straight to object storage through a counting stream, and the scan would read it from there, so no upload ever sits whole in memory.
- **Re-encoding images.** Decoding an image and writing a fresh one throws away anything hidden in it, metadata included. It costs CPU and a decoder's own attack surface, which is why it runs in a sandboxed worker.
- **An asynchronous scan.** A queue would take the scan out of the request, and the client would poll the file's status or be told by a webhook.

### Correctness

No request reads more than `MAX_BODY_BYTES` of a body: `readBody` returns before reading when the declared length is over, and returns from the loop the moment the count passes it, which destroys the request. No path holds anything a request carried: every path is `join(<folder>, id)` with an id from `randomBytes`, found in the store's map, and `GET /files/{id}` looks the id up in that map before any path is built. A file is served only from `files/`, and only `release` puts bytes there, after a verdict of `clean`; every other outcome of `scan` is `pending` or `infected`, so a scanner that fails cannot release anything. The quota check and the record that holds the file's room happen with no `await` between them, so no other request runs in between. A link's signature covers the id and the expiry, so changing either fails `checkLink` before the expiry is read.

### Complexity

- Time: per upload — one pass over the body, one over the bytes to sniff and search, a hash, and at most 3 scanner requests of 1 s each with 0.75 s of waiting, or up to 2 s with `Retry-After`
- Space: per upload — one body of at most `MAX_BODY_BYTES` and its decoded bytes; the records grow with the files

### Trade-offs

Refusing a declared `Content-Length` before reading is cheap and stops the obvious case, but only the running count stops a chunked body or a client that stalls. Both are needed. Refusing with `Connection: close` costs the client a new connection, which is right for someone who sent too much.

Requiring the extension to match the bytes refuses a user whose photo is named `photo.png` but is a JPEG. A friendlier service would rename it; this one refuses, because the name ends up in the download's `Content-Disposition`, and a mismatched extension decides how the user's own machine opens the file.

The active-content check is a denylist, and denylists miss things: escaped PDF names, markup split by encodings. It catches the common polyglots, and the headers do the real work: a browser told `image/png` with `nosniff` will not run the file as a page.

Scanning inside the upload request makes the verdict immediate, at the cost of slow uploads when the scanner is slow. Failing closed means a scanner outage stops every upload from being served, which is the point: an outage of the safety check is not a reason to skip it.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden case, and the failure names what it did.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Reads the whole body, then checks its size | A client decides how much your service holds and how long it waits | `h1` and `h2`: the body never ends, so the starter's 2 s request limit answers `status: expected 413, got 408`, and without it the case times out |
| Checks `Content-Length` and nothing else | A chunked body declares no length | `h2` |
| Stores the file under its name | The next upload of `avatar.gif` replaces it, whoever sends it | `h5`, `h6`: `body: expected "GIF89a...", got ...` |
| Joins the name to a folder | `../h7-ana/avatar.gif` writes into another user's folder, and `../../etc/passwd.gif` out of the data directory | `h7`, `h8` |
| Keeps the whole name as metadata | `C:\Users\kim\Pictures\avatar.png` is not a file's name | `h9`: `body.name: expected "avatar.png"` |
| Counts the quota in base64 characters | Base64 is a third larger than the bytes it carries | `v4`, `h13`, `h14` |
| Checks the quota, awaits the write, then records the file | Uploads that arrive together all pass the check | `h15`: `8 requests at once: expected 2 to answer 201 and 6 to answer 507` |
| Trusts the client's `content_type` | A page can claim to be `image/png`, and a PNG claimed as `text/html` would be served as a page | `v6`, `h18`, `h19` |
| Trusts the extension | A page named `avatar.png` is still a page, and a PNG named `.gif` is no GIF | `v6`, `v8`, `h20`, `h21` |
| Sniffs the type, and nothing else | A real GIF or PNG can carry a page, and a PDF can carry script | `h23`, `h24`, `h25` |
| Serves without `nosniff`, or every type inline | A browser that guesses can run a file as a page; a PDF opened in the page runs in your domain | `v5`, `v7`, `h18`, `h27` |
| Serves a file while its scan is pending | Quarantine that serves is no quarantine | `v11`, `h29`, `h30`, `h31`, `h36`: `step 2 GET /files/{{id}}/content: status: expected 409, got 200` |
| Treats a scanner that fails as clean | An attacker who can slow the scanner gets every file through | `v11`, `h29` to `h33`, `h36`, `h37`, `h39`, `h41`: `step 1 POST /files: status: expected 202, got 201` |
| Retries every failure, a 4xx and a broken answer included | Neither changes on a second try, and each retry is load on the vendor | `h31`, `h32`, `h33`: the count |
| Retries at once, or ignores `Retry-After` | The vendor asked you to wait | `v11`, `v12`, `h38`, `h39`: the gap |
| Lets a rescan of a clean file ask the scanner | It costs a scan, and could turn a clean file pending | `h40` |
| Signs the id alone, or puts the expiry outside the signature | A link can be moved to another file, or extended forever | `h43`, `h44` |
| Checks the expiry before the signature | A forged link learns whether it expired | `v14`, `h48` |

**Edge cases.**

- A body of exactly `MAX_BODY_BYTES` is within the limit, and one byte more is not (`h3`, `h4`).
- `photos/..` and `photos/` have nothing left to show once the folders go, and a `"` would break the `Content-Disposition` header (`h10`).
- `GIF89` is five bytes of a six-byte signature: no type (`h26`).
- `report.pdf.png` with a PDF's bytes is a mismatch: only the last extension counts, and it says PNG (`h21`).
- A JPEG may be `.jpg` or `.JPEG`; the extension is compared in lower case (`h22`).
- A pending file holds its quota, since its bytes are kept, and gives it back when it is found infected or deleted (`h37`, `h41`).
- A 502 whose body is an HTML page is a 5xx, and is retried: never parse an error page as a verdict (`h30`).
- `/files/..%2F..%2Frecords/content` names no id this service gave, so it is 404 before any path exists (`h17`).
