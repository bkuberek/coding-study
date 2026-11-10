# RAG Service with Citations (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per chunk | default answer: each document is cut into overlapping word windows and embedded in one call, retrieval is one exact cosine query in Postgres, the model sees the retrieved chunks alone, and only the citations it was shown survive |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Cut documents into overlapping chunks, embed them in one call, keep each with its source, and wait out a 429 | `chunksOf` and `chunkCount` in `src/chunking.ts`, `embed` with `sentWithRetries` in `src/models.ts`, the `chunks` table, and `putDocument` with `replaceChunks` |
| 2 | The `k` chunks most like a query, at or above a minimum score | `nearest` in `src/store.ts`, one cosine query, and `search` in `src/assistant.ts` |
| 3 | Answer from the retrieved chunks alone, cite them, and say "I don't know" without the model when nothing passed | `prompt`, `complete` reading the model's JSON, and `ask`, which returns before the model when retrieval found nothing |
| 4 | Updates leave no stale chunk, and citations the model was not shown are dropped | `replaceChunks` deleting and inserting in one transaction after the embeddings came back, and `grounded` |

## Approach: reference (Embed each document in one call, rank by cosine in Postgres, and keep only the citations that were retrieved)

### Intuition

A chat model on its own answers from what it absorbed in training, which says nothing about this team's refund window. Retrieval-augmented generation hands it the right passages at question time and asks it to answer from those alone. Every level of this project is one link of that chain, and each link fails in its own quiet way.

Chunking decides what can be found. A whole document is too coarse to rank and too long to send, and a sentence too small to carry its context, so the documents are cut into windows of 20 words. A fact that falls across a boundary would be split between two chunks and found in neither, so each window repeats the last 5 words of the one before. Every chunk keeps its document and position, because a citation that cannot say where it came from is not a citation.

Embedding turns each chunk into a vector, so that "how long do customers have" lands near "within 30 days of purchase" though they share few words. Embedding APIs are paid and rate-limited per request, so a document's chunks go in one request, and a 429 is a request to wait, not a failure.

Retrieval is a nearest-neighbour search: the cosine similarity of the question's vector with every chunk's, best first. Two limits shape it. `k` caps how much context the model gets, and the minimum score decides when the corpus simply does not cover the question. That second limit is the honest "I don't know": with nothing close enough, the model would only guess, so it is not asked at all.

Generation is where grounding is lost or kept. The model must see the retrieved chunks and nothing else, so that what it says can only come from them; sending the whole corpus defeats retrieval and costs a fortune at any real size. And the model's citations are claims, not facts: it can cite a chunk it never saw. The app knows exactly what it showed, so it keeps only those.

Updates close the loop. A document put again must leave nothing of its old version behind, or the assistant keeps quoting a policy that no longer holds.

### Say it out loud

"I split the text on whitespace and take windows of 20 words, starting every 15, stopping right after the window that reaches the end, so there is never a short last chunk that only repeats the one before. A document over 8 chunks is refused before I call anything. All the chunks of a document go to the embeddings service in one request; a 429 waits for `Retry-After` and tries again, three tries in all, and anything else is a 502.

"Each chunk is a row: document id, position, text and a `vector(9)`. Putting a document embeds first and then, in one transaction, deletes its old rows and inserts the new ones, so a failed embedding changes nothing and a shorter version leaves no tail behind.

"Search embeds the query alone and runs one query: one minus pgvector's cosine distance as the score, filtered by the minimum, ordered by distance, then document id in code-point order and position, limited to `k`. It is an exact scan: at this size an approximate index would only risk missing a chunk.

"Asking retrieves with the defaults. If nothing passes 0.6, the answer is 'I don't know' and the model is never called. Otherwise the model gets the system prompt and one user message whose parts are the retrieved chunks, tagged with their ids, then the question. Its reply is JSON I parse and check. Of its citations I keep the ones I showed it, each once, in its order, and drop the rest."

### Algorithm

1. `PUT /documents/{id}`: check the id and that the text has a word, else 400. Count the chunks from the word count, `ceil((words - 20) / 15) + 1` above 20 words; over 8 is 413. Cut the chunks, embed them in one request, then replace the document's rows in one transaction. Answer the count.
2. `GET /documents/{id}/chunks`: the rows of the document by position, or 404 when there are none.
3. `POST /search`: check `query`, `k` and `min_score`, else 400. Embed the query alone; run the cosine query; round each score to 4 decimals.
4. `POST /ask`: check the question; retrieve with `k` 3 and minimum 0.6. None: "I don't know." with no citations. Otherwise send the system prompt and the parts `[<id>] <text>`, best first, then `Question: <question>`; parse the reply's content as `{answer, citations}`, else 502; keep each citation that names a retrieved chunk, the first time it appears.
5. Every model call: at most 3 tries, waiting `Retry-After` whole seconds, or 1, after each 429; any other status but 200, a timeout or an unreadable body is a 502 naming the service.

### Design

| File | Holds |
|------|-------|
| `src/chunking.ts` | `wordsOf`, `chunksOf` and `chunkCount`, with the window's size, overlap and the most chunks a document may have |
| `src/models.ts` | `embed` and `complete` over the starter's clients, `sentWithRetries`, the 429 loop, and `ProviderError`, which names the service that failed |
| `src/store.ts` | The `chunks` table: `replaceChunks`, `chunksOfDocument` and `nearest`, the cosine query |
| `src/assistant.ts` | What each route does: `putDocument`, `listChunks`, `search` and `ask`, with `prompt` and `grounded` |
| `src/requests.ts` | The checks on each request's body and the document id |
| `src/server.ts` | The routes, and a `ProviderError` turned into a 502 with its code |
| `src/providers.ts`, `src/db.ts` | The starter's, unchanged |
| `migrations/0002_chunks.sql` | The `chunks` table, keyed by document and position |

`src/assistant.ts` returns plain results, never HTTP answers, so the routes alone know status codes. The retry lives once in `src/models.ts` and serves both services; each service's function only reads what came back, so a new failure mode is a change in one place.

### Correctness

Chunking: the windows start at 0, 15, 30, and so on, and the loop stops after the first window whose end reaches the last word, so the windows cover every word, consecutive windows share exactly 5 words, and no window lies wholly inside the one before. `chunkCount` is the same arithmetic without the slicing, and a test checks the two agree for every length from 1 to 200 words, so the 413 is decided without cutting anything.

Updates: the embeddings are requested before the transaction starts, so a failed or rate-limited call returns before any row changes. Inside the transaction the delete removes every row of the document, whatever its old length, and the insert adds the new ones, so after the commit the document's rows are exactly its new chunks, and a concurrent reader sees one version or the other. Retrieval reads only rows, so no stale chunk can be scored, shown to the model or cited.

Retrieval: the score is the cosine similarity, `1 - (a <=> b)`, computed for every row; the filter and the order use that same expression, and the order breaks ties by document id in code-point order and then position, so the result is the statement's for any data. The stand-in's vectors are small whole numbers, which float4 holds exactly, so Postgres and a computation in the app agree to within rounding.

Grounding: the model is called only when retrieval found something, and is shown exactly the retrieved chunks. A citation survives only if its id is in the map of those chunks, and only the first time, so every citation in an answer names a chunk the model was shown, once.

### Complexity

- Time: per request — a put embeds its at most 8 chunks in one call and writes them in one transaction; a search embeds one text and scans every chunk once, linear in the corpus; an ask adds one chat call and a pass over at most 3 citations
- Space: per chunk — one row with its text and 9 numbers

### Trade-offs

The exact scan is linear in the number of chunks, which is nothing at a few dozen and slow at millions. pgvector's HNSW index answers in roughly logarithmic time, but it is approximate: it can miss a true neighbour, and with a filter such as the minimum score it can return fewer than `k` rows even when more qualify, unless its search width (`hnsw.ef_search`) is raised or its iterative scans (`hnsw.iterative_scan`, since pgvector 0.8) are turned on. The reference stays exact because the cases expect the exact top `k`, and a corpus that needs the index also needs a way to measure what it misses.

Fixed word windows are the simplest chunking that is easy to state and grade. Real systems cut by tokens, which is what both the embedding model and the chat model count, and prefer boundaries that mean something, headings, paragraphs, sentences, so a chunk is a coherent passage rather than 20 words that start mid-sentence. The overlap is a hedge against bad boundaries; better boundaries need less of it.

Putting a document always embeds it again, even when its text did not change. Storing a hash of each chunk's text and embedding only the changed ones would cut the cost of re-ingesting a corpus nightly; the cases do not ask for it.

Grounding by id is cheap and exact about what was shown, but it does not check that the cited chunk supports the sentence it is attached to. A model can cite a real retrieved chunk for a claim that chunk never makes. Checking that needs another model call, or a human, and is where evaluation sets earn their keep.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a case, and the failure names what it did, with the case's note saying what was expected. The first two rows were run on a real stack, on top of the reference, with the messages shown; neither is stored as a solution. The others name the cases written to catch them.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Sends every chunk of the corpus to the model instead of the retrieved ones, while still citing from the retrieved | Retrieval no longer limits what the model sees, so its answer can come from anywhere, and the prompt grows with the corpus | The 11 cases that read the prompt, `v7`, `v9`, `h29` to `h35`, `v11` and `h43`, and nothing else: `chat answer-refund-window with header Authorization="Bearer cs-fake-llm-key", body {"model": "help-chat-1", "messages": ...: expected 1 request, saw 0` |
| Passes the model's citations through unchecked | The model cites chunks it was never shown, or that do not exist | The 5 cases whose model cites what it was not shown, `v12`, `h43` and `h46` to `h48`: `body.citations: expected 2 elements, got 3; body.citations[1].chunk_id: expected "refunds:2", got "refunds:7"` |
| Chunks with no overlap, starting every 20 words | A fact across a boundary is in neither chunk, and the stand-in knows no such chunks | `v1`, `v2`, `h3`, and every later case, since no put succeeds |
| Adds a last window that starts every 15 words regardless, so a 35-word text gets a third chunk of 5 words | The last chunk only repeats the one before | `h4`, and `h6` for 8 chunks |
| Embeds one chunk per request | One request per chunk is what rate limits punish, and the stand-in knows only whole documents | `v1`, `h6`, and every case that puts a document of more than one chunk |
| Treats a 429 as a failure, or retries at once, or forever | The service asked for a wait, and a client that ignores it is the reason for the limit | `v3`, `h13`, `h37`, `h38` |
| Retries a 503 | A service in trouble gets more load | `h14`, `h39` |
| Counts chunks after embedding them, so a 9-chunk document reaches the service | The refusal costs a paid call | `h7` |
| Calls the model when nothing passed the minimum | The model guesses, and the call costs money | `v8`, `h36` |
| Sends the top `k` regardless of the minimum score | Chunks that do not match reach the model | `h20`, `h34` |
| Cites every retrieved chunk instead of the model's citations | An answer cites sources it did not use, and "I don't know" comes with citations | `v7`, `v9` |
| Upserts by document and position on an update | A shorter new version leaves its old tail, `refunds:3` and `refunds:4`, to be retrieved and cited | `v10`, `v11`, `h42`, `h43` |
| Deletes the old chunks before the embeddings came back | A failed update loses the document | `h45` |
| Inserts on every put without deleting | The same text put twice is found twice | `h44` |
| Orders ties by the database's collation, or not at all | Equal scores come back in an order the statement does not give | `h21` |

**Edge cases.**

- A text of 20 words is one chunk, 21 words are two, and 35 words are two, the second ending at the last word (`h2` to `h4`).
- Spaces, tabs and newlines in any run separate words, and a chunk's text has single spaces (`h5`).
- 8 chunks are allowed and sent in one request; 9 are refused before anything is sent, and nothing is kept (`h6`, `h7`).
- A put that fails at the embeddings service, after 3 tries of 429 or one 503, keeps nothing (`h13`, `h14`).
- Two documents each list their own chunks only (`h15`).
- Fewer than `k` chunks may pass the minimum, and on an empty database none does (`h20`, `h23`).
- `k` of 0, 11 or 2.5, a minimum of 1.5 and a query of spaces are refused without embedding anything (`h24` to `h28`).
- The model's own "I don't know" comes with no citations (`v9`); a reply that is not the JSON asked for is a 502 (`h40`).
- A citation repeated by the model is kept once, at its first place, and an answer whose citations were all invented keeps its text with none (`h47`, `h48`).
