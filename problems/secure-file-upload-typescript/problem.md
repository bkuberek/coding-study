# Secure File Upload (TypeScript)

## Statement

Your service lets its users upload files, such as an avatar or an invoice attached to a ticket, and serves them back. Every part of an upload is written by whoever sent it: its size, its name, the type it claims, and the bytes themselves. A body can be far larger than it says, or never end. A name can climb out of its folder with `../`. A page full of script can call itself `avatar.png`, and a browser that guesses types will run it on your domain. A file can carry malware, and the scanner that would catch it can be down.

Build the service in levels. It takes uploads within a size limit and a quota, stores them under names it chose, decides what a file is from its bytes, keeps every file in quarantine until a malware scanner clears it, and lets an owner share a file through a signed link that expires. `cstudy` runs your app in a Docker sandbox and judges it by what it answers over HTTP and by what it asked the scanner. The service and its vendor are invented.

## Input

HTTP requests. An upload is `POST /files` with a JSON body that carries the file as base64, the way many APIs take an avatar or an attachment from a browser or a phone app. The other requests read, delete, scan and share stored files. Each level says what it adds.

Every request but `GET /health` and, from level 4, `GET /shared/{id}` names its user in `X-User`: 1 to 64 letters, digits, `-` or `_`. A gateway in front of your service has already checked who that is, so trust it. A request without a valid `X-User` answers 401 with `{"error": "unauthenticated"}`, before anything else is read.

## Output

JSON with `Content-Type: application/json`, except a file's own bytes. A refusal is `{"error": "<code>"}`, with the codes each level names. A file id this service never gave, or one that belongs to another user, answers 404 with `{"error": "not_found"}` to every request, so nobody learns which files exist. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200 once it is ready.

## Project

`cstudy start` copies the service into `projects/secure-file-upload-typescript/`, and `cstudy dev` runs it with its mock server. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, and where the server starts. It stores and serves files, under the names they came with. Its server gives a client 2 s to send a whole request, and then answers 408: that bounds how long a request can take, and nothing about how much it holds.
- `tests/`: your tests, run by `cstudy test`, with `tests/mockControl.ts` to set the scanner's visible scenario from a test and read what it received.
- `vendors/scanner/API.md`: what the scanner does, for reading. Nothing depends on this copy.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings. Your app's environment already holds it.

Keep files in `CSTUDY_DATA_DIR`. It survives restarts in `cstudy dev`, and each test or graded run starts with an empty one. `MAX_BODY_BYTES` is 2,048 and `QUOTA_BYTES` is 1,024, small so that a case's upload fits in a few lines; your code reads them, and works the same with any value.

`cstudy test` starts a sandbox, runs your tests beside the app, and then the visible cases of your open levels. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers. To watch a failure yourself, run `cstudy dev --scenario scanner=outage` and ask with `curl`.

## Level 1: Upload and serve

`POST /files` uploads a file:

```json
{"name": "avatar.gif", "content_type": "image/gif", "data": "R0lGODlhAQABAAAAACwAAAAAAQABAAACAkQBADs="}
```

| Field | Rule |
|-------|------|
| `name` | The file's name on the user's machine: a string |
| `content_type` | Optional: what the client says the file is. Your app never uses it |
| `data` | The file's bytes in standard base64: `A` to `Z`, `a` to `z`, `0` to `9`, `+` and `/`, padded with `=` to a multiple of 4 characters. At least one byte |

It answers 201 with the file's record:

```json
{"id": "9f2c4e0a7b1d48e6a3c5f7091b2d4e6f", "name": "avatar.gif", "size": 29, "sha256": "<64 hex digits>"}
```

- `id` is new for each upload: 32 lowercase hex digits from a secure random source. It is the file's storage key. Never derive anything you store from the name: two users can both upload `avatar.gif`, and one user can upload it twice. Each upload is a new file.
- `name` is metadata, shown and later offered as the download's name, and never part of a path. Keep only what follows its last `/` or `\`, since old browsers sent a whole client path such as `C:\Users\kim\avatar.png`. What is left must be 1 to 255 characters of printable ASCII, from space to `~`, with no `"`, and neither `.` nor `..`.
- `size` counts the file's bytes, decoded, and `sha256` is their SHA-256 in lowercase hex.

**The size limit holds while the body arrives.** A request body may hold at most `MAX_BODY_BYTES` bytes, the JSON included. A body that declares a larger `Content-Length` is refused from its headers, before your app reads any of it. A body sent in chunks declares no length, so count its bytes as they arrive, and refuse it the moment the count passes the limit: a client can send forever, or stop sending without ever finishing. Never read a whole body to find out how big it was. Answer such a refusal with `Connection: close`, since the rest of the body is never read.

**The quota.** Each user may keep at most `QUOTA_BYTES` bytes, counted as the `size` of their files. An upload that would take them past it is refused, and a refused upload takes nothing. Two uploads that arrive at once must not both fit in room for one.

| Request | Status | Body |
|---------|--------|------|
| A body over `MAX_BODY_BYTES` | 413 | `{"error": "too_large"}` |
| A body that is not a JSON object, a `name` that is not a string, or `data` that is not base64 of at least one byte | 400 | `{"error": "invalid_request"}` |
| A `name` with nothing left to show, or one that breaks its rule | 400 | `{"error": "invalid_name"}` |
| An upload past the user's quota | 507 | `{"error": "quota_exceeded"}` |

An upload is checked in the order of this table, after `X-User`.

| Request | Answer |
|---------|--------|
| `GET /files/{id}` | 200 with the file's record, as the upload answered it |
| `GET /files/{id}/content` | 200 with the file's bytes, and their `Content-Length` |
| `DELETE /files/{id}` | 204, with no body. The file and its bytes are gone, and so is their room in the quota |
| `GET /usage` | 200 with `{"used_bytes": 800, "quota_bytes": 1024}`: what the user keeps, and their quota |

At this level, serve every file as `Content-Type: application/octet-stream` with `Content-Disposition: attachment; filename="<name>"`: a download, whatever it is. Level 2 decides what may be shown.

### Example 1

<!-- case: v1 -->

The upload's record keeps the name as it came, and its id is the one the upload answered.

### Example 2

<!-- case: v2 -->

The bytes come back exactly as they went up.

### Example 3

<!-- case: v3 -->

The body is 2,132 bytes, more than the 2,048 `MAX_BODY_BYTES` allows.

### Example 4

<!-- case: v4 -->

Two invoices of 400 bytes take 800 of the 1,024 bytes `v4-ana` may keep. A third would take 1,200, so it is refused, and takes nothing.

## Level 2: Trust the bytes

The client's `content_type` is a claim, and so is the name's extension. What a file is comes from its first bytes, its magic number. Allow these types and nothing else:

| Type | The file starts with | Extensions | Served |
|------|----------------------|------------|--------|
| `image/png` | The bytes `89 50 4E 47 0D 0A 1A 0A` | `png` | `inline` |
| `image/jpeg` | The bytes `FF D8 FF` | `jpg`, `jpeg` | `inline` |
| `image/gif` | `GIF87a` or `GIF89a` | `gif` | `inline` |
| `application/pdf` | `%PDF-` | `pdf` | `attachment` |

A file can be two things at once. A real GIF can carry a page in a comment, and a browser that guesses types, or a viewer that runs a PDF's script, will find it. Refuse a file that holds active content:

- anywhere in the file, ignoring case: `<!doctype`, `<html`, `<head`, `<body`, `<script`, `<iframe` or `<svg`;
- in a PDF, the names that run script when it opens: `/JavaScript` or `/JS`.

| Request | Status | Body |
|---------|--------|------|
| Bytes that start as no allowed type | 415 | `{"error": "unsupported_type"}` |
| A name whose extension, after its last `.` and in any case, is not one of that type's | 415 | `{"error": "type_mismatch"}` |
| A file that holds active content | 415 | `{"error": "active_content"}` |

These come after `invalid_name` and before the quota, in the order of this table. A name with no extension is a mismatch.

Serve a file's content with:

- `Content-Type`: the type its bytes proved, as the table writes it;
- `X-Content-Type-Options: nosniff`, so the browser takes that type as given and guesses nothing;
- `Content-Disposition: inline; filename="<name>"` for an image, and `attachment; filename="<name>"` for a PDF, which is only ever downloaded.

### Example 1

<!-- case: v5 -->

A PNG is served as `image/png`, inline, with its name.

### Example 2

<!-- case: v6 -->

The name says PNG and so does the client, and the bytes are a page with a script.

### Example 3

<!-- case: v7 -->

A PDF comes back byte for byte, as a download.

### Example 4

<!-- case: v8 -->

A real JPEG, named `photo.png`.

## Level 3: Quarantine until clean

Every upload is scanned for malware before anyone can download it. After the checks and the quota, store the file in quarantine and ask the scanner, as `vendors/scanner/API.md` describes: `POST {SCANNER_URL}/v1/scan` with the file's bytes, `Authorization: Bearer {SCANNER_API_KEY}` and `X-Content-Sha256`.

- A request to the scanner has 1 s, from sending it to the last byte of its answer.
- A scan makes up to 3 attempts. Try again after a timeout, a lost connection, a 429 or a 5xx. Wait 250 ms after the first failed attempt and 500 ms after the second, except that after a 429 with a `Retry-After`, you wait as many seconds as it says.
- A 200 with `{"verdict": "clean"}` or `{"verdict": "infected", ...}` is a verdict. Any other answer, a 4xx, a body that is not JSON, or a verdict of anything else, ends the scan at once with no verdict: it will not change on a retry.

A file is `pending` until a scan gives a verdict. Only `clean` releases it. A scanner that cannot answer is no reason to let a file through: the scan **fails closed**.

| Verdict | The upload answers | The file |
|---------|--------------------|----------|
| `clean` | 201, with the record | Released, and served |
| `infected` | 422 with `{"error": "infected"}` | Deleted, with nothing kept |
| None | 202, with the record | `pending`: kept in quarantine, never served |

| Request | Answer |
|---------|--------|
| `GET /files/{id}/content` of a pending file | 409 with `{"error": "scan_pending"}` |
| `GET /files/{id}/content` of an infected file | 410 with `{"error": "infected"}` |
| `GET /files/{id}/scan` | 200 with `{"status": "pending"}`, `"clean"` or `"infected"` |
| `POST /files/{id}/scan` | Scans a pending file again, by the same rules, and answers 200 with its status. A file found infected now keeps its record, so its owner can see what happened, and loses its bytes. A file that is not pending asks the scanner nothing, and answers its status |

A pending file counts toward its owner's quota, since its bytes are kept. An infected file counts for nothing. `GET /files/{id}` answers a file's record whatever its status.

### Example 1

<!-- case: v9 -->

One request to the scanner, which carried the key and the file's hash.

### Example 2

<!-- case: v10 -->

With the scanner's `infected` scenario, the upload is refused, and `v10-ana` keeps nothing.

### Example 3

<!-- case: v11 -->

With the scanner's `outage` scenario, every attempt answers 503: three requests, at least 250 ms apart, and the file stays pending.

### Example 4

<!-- case: v12 -->

With the scanner's `rate_limited_then_clean` scenario, the first attempt answers 429 with `Retry-After: 1`. The second request comes a second later, and the file is clean.

## Level 4: Links that expire

An owner can share a clean file with someone who has no account, for a while.

`POST /files/{id}/links` with `{"expires_in_s": 60}` creates a link. `expires_in_s` is a whole number of seconds from 1 to 3,600. It answers 201 with the link's path in `Location`, and the same path in its body with the moment it expires:

```json
{"url": "/shared/9f2c4e0a7b1d48e6a3c5f7091b2d4e6f?expires=1794286840&sig=602d1ef8...", "expires": 1794286840}
```

- `expires` is now in Unix seconds, rounded down, plus `expires_in_s`, written in decimal.
- `sig` is the HMAC-SHA256 of the text `<id>.<expires>`, keyed with `LINK_SIGNING_KEY`, in lowercase hex. Changing the id or the expiry breaks it, and only your service holds the key.

| Request | Status | Body |
|---------|--------|------|
| A body that is not a JSON object, or an `expires_in_s` that breaks its rule | 400 | `{"error": "invalid_request"}` |
| A pending file | 409 | `{"error": "scan_pending"}` |
| An infected file | 410 | `{"error": "infected"}` |

These come after `not_found`, in this order.

`GET /shared/{id}?expires=<expires>&sig=<sig>` needs no `X-User`. Check the signature first, comparing it in constant time, so a forged link learns nothing, not even whether it expired:

| Request | Status | Body |
|---------|--------|------|
| No `expires` or `sig`, an `expires` that is not a decimal number, a `sig` that is not 64 lowercase hex digits, or a signature that does not match | 403 | `{"error": "invalid_link"}` |
| The time is `expires` or later | 410 | `{"error": "link_expired"}` |
| A file deleted since | 404 | `{"error": "not_found"}` |

Otherwise it serves the file's content exactly as `GET /files/{id}/content` does, with the same headers.

### Example 1

<!-- case: v13 -->

The link's path is in the `Location` of the answer that created it, and opening it needs no `X-User`.

### Example 2

<!-- case: v14 -->

The same link, with its signature replaced by zeros.

### Example 3

<!-- case: v15 -->

With the scanner's `outage` scenario, the file is still pending.

## Constraints

- No request ever reads more than `MAX_BODY_BYTES` of a body, or waits for the end of one already past it.
- No path your app writes or reads is built from anything a request carried, except an id it looked up among the ones it gave.
- A file's type comes from its bytes alone.
- No file is served, or shared, before its scanner said `clean`.
- At most 3 requests to the scanner per scan, and a wait never comes up short: the cases measure the gap between an answer and your next request.

## Follow-ups

- The service decodes a whole upload in memory, which a limit of 2 KiB allows. With a limit of 100 MB, how would you take the upload straight to storage, still counting as it arrives, and what would you scan then?
- Many services serve user files from a domain of their own, with nothing else on it. What does that protect that `nosniff` and `Content-Disposition` do not?
- The active-content check is a list of strings, and PDF names can be written with escapes such as `/J#61vaScript`. Why is a denylist like this one weak, and what would you rely on instead?
- A scan here happens inside the upload request, so a slow scanner makes a slow upload. How would a queue change that, and how would the client learn the verdict?
- A pending file waits for someone to call `POST /files/{id}/scan`. What should call it, how often, and what should happen to a file that stays pending for a week?
- A link cannot be revoked before it expires, except by deleting the file. What would you store to revoke one link, and what does that cost each time a link is opened?
- A name in another script, such as `résumé.pdf`, is refused here. How does RFC 6266's `filename*` carry it safely in `Content-Disposition`?

## Hints

### Hint 1

Check `X-User` and the declared `Content-Length` before you touch the body. Then read it with `for await (const chunk of request)`, add each chunk's length to a count, and return the refusal as soon as the count passes the limit. Returning from inside the loop stops the reading.

### Hint 2

Make the id with `randomBytes(16).toString("hex")`, and build every path from it alone: `join(dataDir, "files", id)`. Keep the name in a record beside it. Then no name can reach a path, however it is written.

### Hint 3

Check the quota and record the file in one synchronous step, before any `await`. Node runs one piece of JavaScript at a time, so nothing can come between a check and a write that no `await` separates.

### Hint 4

`bytes.subarray(0, 8).equals(signature)` compares a file's first bytes. `bytes.toString("latin1")` gives one character per byte, so a search for `<script` finds it wherever its bytes are, even in binary.

### Hint 5

Write the scan as a loop of at most 3 attempts around one function that answers a verdict, "try again", or "give up". `AbortSignal.timeout(1000)` on `fetch` covers the answer's body too. Start from "pending" and let only a verdict of `clean` change it.

### Hint 6

`createHmac("sha256", key).update(text).digest()` signs, and `timingSafeEqual` compares two buffers of the same length without stopping at the first difference. Check the signature's shape before you compare, since `timingSafeEqual` throws on buffers of different lengths.
