# Review: Pagination API: Reference

Verdict: request changes. The change breaks every installed mobile app, lets any customer read any other customer's orders, and builds pagination that duplicates and skips orders for exactly the customers who asked for it. A strong review treats the response shape as a contract problem first, proposes the cursor design the API already uses for invoices, and asks what support actually needs instead of patching the `customerId` line.

A design to suggest, consistent with `/v1/invoices`:

```text
GET /v1/orders?limit=50&cursor=<opaque>
  keyset query: WHERE customer_id = $1 AND (created_at, id) < ($2, $3)
                ORDER BY created_at DESC, id DESC LIMIT $limit + 1
  cursor = base64url of (created_at, id) of the last row returned
  index: (customer_id, created_at DESC, id DESC)
Old clients that send no pagination parameters keep getting the array of the latest 500,
or the paginated shape ships as a new versioned endpoint.
```

## Blocker

- `orders.ts:43-48` response shape: `GET /v1/orders` changes from a JSON array to `{data, page, pageSize, total}`. Every app version that parses an array breaks on deploy, and 30% of active users cannot update; partners break too. The snapshot update in `orders.test.ts.snap` is this breaking change, approved by the test. Keep the existing contract for requests without pagination parameters (or add a versioned endpoint) and coordinate a deprecation window with the mobile teams.
- `orders.ts:26-27`: `customerId` from the query string overrides the authenticated customer, with no role check. Any logged-in customer can list any other customer's orders by changing one parameter (an insecure direct object reference). Remove it; support tooling already has admin endpoints with a support role, so ask what the support use case needs and add it there.

## Major

- `orders.ts:32-37` offset pagination over a set that keeps growing: when new orders arrive between page requests, every later page shifts down, so the client sees duplicates; deletions or status-based filtering would cause skips. Ordering only by `created_at` is not deterministic when bulk imports share a timestamp, so rows can swap between pages even without new orders. Use keyset (cursor) pagination on `(created_at, id)` with a unique tiebreaker, as above.
- `orders.ts:37` performance: `OFFSET` makes Postgres read and discard every skipped row, so page 1,000 of a 2-million-order customer reads 20,000 rows to return 20, and a crafted `page=100000000` is a cheap way to load the database. Keyset pagination makes every page cost the same.
- `orders.ts:39-41`: `SELECT COUNT(*)` on every page scans the customer's whole index range (2 million entries for the largest customers) to compute `total`. Drop `total` (cursor clients do not need it), or make it opt-in and approximate. It is also computed in a separate query, so it can disagree with the page it accompanies.
- `orders.ts:24` and `orders.ts:50` error shapes: the 400 is a plain-text body and the 500 is `{message}`, while every other endpoint returns `{"error": {"code", "message"}}` through `sendError`. Clients that branch on `error.code` crash or show nothing. Use `sendError(res, 400, "invalid_parameter", ...)` and `sendError(res, 500, "internal_error", ...)`.
- `orders.ts:50`: the 500 response returns the raw database error message to the client (table names, query fragments), and the `req.log.error` call that used to record it was removed, so failures are now invisible to the team. Log the error, return the generic message.
- `orders.ts:21-25` validation: negative `page` or `pageSize` values pass (`parseInt("-5") || 1` is `-5`) and reach Postgres as a negative `LIMIT` or `OFFSET`, which errors, which then returns 500 with the leaked message. Validate with the zod schemas used elsewhere: integers, `limit` between 1 and 100, cursor decodable; return 400 otherwise.

## Minor

- `orders.ts:21-22` naming: `page` and `pageSize` (camelCase) next to `/v1/invoices`' `limit`, `cursor` and `next_cursor` (snake_case). One API, one pagination vocabulary.
- The default page size changes the behavior for clients that send no parameters from 500 orders to 20 even after the shape issue is solved; decide deliberately which default old clients get.
- `orders.test.ts`: the new test only checks counts, with 30 orders that may share a timestamp. Add tests for: an order inserted between page requests (no duplicate, no skip), ties on `created_at`, another customer's orders never visible, invalid parameters returning the standard error shape, and the old contract for requests without parameters.
- `orders.ts:27`: `req.query.x as string` hides that Express can give an array (`?page=1&page=2`); the zod schema fixes this too.

## Nit

- `orders.ts:26`: the comment documents the authorization hole as a feature; with the parameter gone, it goes too.
- `orders.ts:9-10`: `DEFAULT_PAGE_SIZE` and `MAX_PAGE_SIZE` belong with the pagination helpers `/v1/invoices` uses, so every list endpoint shares limits and cursor encoding.
- Consider a `Link` header with `rel="next"` alongside `next_cursor` for generic HTTP clients.
