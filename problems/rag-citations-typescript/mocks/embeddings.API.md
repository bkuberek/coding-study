# The embeddings service

The team's embedding model, `help-embed-1`, behind a small HTTP API. It turns each text it is given into a vector of 9 numbers, so that texts about the same thing get vectors that point the same way. Your app reaches it at `EMBEDDINGS_URL`, with the key in `LLM_API_KEY`. This is its contract, and it will not change for you.

## `POST /v1/embeddings`

Send the key as `Authorization: Bearer <key>`, and a JSON body with the model and a list of texts, always a list, even for one text:

```json
{"model": "help-embed-1", "input": ["first text", "second text"]}
```

It answers 200 with one vector per text, in the order of `input`, each with its `index` there:

```json
{"object": "list", "model": "help-embed-1",
 "data": [{"object": "embedding", "index": 0, "embedding": [1, 9, 0, 0, 0, 0, 0, 0, 6]},
          {"object": "embedding", "index": 1, "embedding": [1, 9, 0, 0, 0, 0, 0, 0, 0]}],
 "usage": {"prompt_tokens": 40}}
```

Compare two vectors by their cosine similarity: the dot product divided by the product of their lengths. Their lengths differ, so a dot product alone does not compare them.

## This one is a stand-in

In the sandbox, `help-embed-1` is a stand-in with no model behind it. It knows the vectors of a fixed set of texts, the ones the cases need, and gives the same vector for the same text every time:

- **A document's chunks**, cut exactly as the statement says, all of one document's in one call, in position order.
- **A question** the cases ask, alone in its list, exactly as the case sends it.

Any other input answers 400:

```json
{"error": {"type": "unknown_input", "message": "help-embed-1 here is a stand-in that knows the vectors of fixed texts only: ..."}}
```

So a 400 from it while you work means your chunks or your batches are not the statement's: one chunk per call, a chunk cut at another place, or two documents in one call. Print the error your app gets, and compare what it sent, which `tests/providerScenario.ts` can read back, with the chunks the statement's examples show.

## When it fails

| Status | Meaning | Headers |
|--------|---------|---------|
| 429 | Too many requests: wait, then send the same request again | `Retry-After`: the whole seconds to wait |
| 5xx | Its own trouble | |

## Scenarios

These are what you can try for yourself. They are not all it can do.

| Name | What it does |
|------|--------------|
| `rate_limited_then_ok` | The first request answers 429 with `Retry-After: 1`, and every later one as usual |
| `outage` | Every request answers 503 |

Run your app against one: `cstudy dev --scenario embeddings=outage`. In a test, the helper in your project's `tests/` does the same.
