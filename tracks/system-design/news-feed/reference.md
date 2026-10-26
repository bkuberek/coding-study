# News Feed: Reference

## Requirements

Clarify before designing:

- **Read-heavy with a skewed write side.** 25 feed loads per post written, but a single celebrity post can touch 100 million feeds. The design question is where to pay for the follower graph: at write time, at read time, or both.
- **Freshness targets differ**: 5 seconds for most followers, 1 minute for all. That one-minute allowance is what lets celebrity posts take a different path.
- **Ranked, not chronological**: ranking interacts with pagination; "no duplicates, no skips" rules out naive offsets.
- **Correctness requirements that are filters, not writes**: deletes, unfollows and blocks must be honored at read time; trying to scrub them from millions of precomputed feeds synchronously does not scale.
- **Out of scope**: ads, recommended posts from accounts not followed, comments, media upload. Name them; candidates from outside the follow graph are a natural extension.

## Estimates

| Quantity | Calculation | Result |
|----------|-------------|--------|
| Posts | 200 M/day | ~2,300/s average, ~7,000/s peak |
| Feed loads | 500 M x 10 | 5 B/day, ~58,000/s average, ~175,000/s peak |
| Fan-out on write (all followers) | 200 M posts x 300 followers | 60 B inserts/day, ~700,000/s average, ~2 M/s peak |
| Fan-out, active followers only | about half of followers are daily active | ~350,000/s average |
| Feed cache | 500 entries x 16 B (post id + author id) x 500 M users | ~4 TB, ~8 TB with 2 replicas |
| Post storage | 200 M x ~1 KB (text, metadata) | ~200 GB/day, ~75 TB/year before replication |
| Celebrity post, pure push | 100 M inserts at a 1 M/s share of fan-out capacity | ~100 s and a backlog for everyone else |

The last row is the argument for a hybrid: pure push breaks on celebrities, pure pull makes every feed load query 300 authors.

## API

```text
POST /v1/posts            Idempotency-Key: <uuid>
  {"text": "...", "media_ids": ["m_123"], "visibility": "followers"}
  201 {"post_id": "1764...", "created_at": "..."}

GET /v1/feed?cursor=<opaque>&limit=20
  200 {"items": [{"post": {...}, "author": {...}, "counts": {...}}], "next_cursor": "...", "new_posts_available": false}

PUT    /v1/follows/{account_id}
DELETE /v1/follows/{account_id}
DELETE /v1/posts/{post_id}
```

The cursor is opaque: it encodes a session snapshot id and a position, never a raw offset.

## Data model

| Data | Store | Key | Notes |
|------|-------|-----|-------|
| Posts | wide-column or sharded relational | `post_id` (time-ordered 64-bit id: timestamp, shard, sequence) | text, author, visibility, `deleted_at` |
| Author timeline | wide-column | `(author_id, post_id desc)` | the author's own posts, also cached for celebrities |
| Follow graph | sharded key-value, both directions | `followers(author_id) -> follower_id` and `following(user_id) -> author_id` | paged reads for fan-out |
| Feed cache | in-memory, sharded by user | `user_id -> [(post_id, author_id)]`, capped at 500 | only for users active in the last 30 days |
| Session snapshot | in-memory, TTL 30 min | `snapshot_id -> ranked post ids` | backs pagination |
| Counters | sharded counters, cached | `post_id -> likes, replies, reposts` | approximate is fine on the feed |
| Celebrity set | config, refreshed hourly | author ids above the fan-out threshold | |

Time-ordered ids give a global rough order without a coordinator and make "newer than" queries cheap.

## High-level design

```text
write: client --> post service --> posts store + author timeline
                              --> event log "post_created" --> fan-out workers
                                     (page through followers, skip inactive users and celebrities)
                                     --> feed cache appends (per follower shard, batched)

read:  client --> feed service
          1. precomputed candidates from the feed cache            (pushed authors)
          2. recent posts of followed celebrities                   (pulled, author timeline cache)
          3. merge, filter (deleted, blocked, unfollowed)           (~500 candidates)
          4. ranking service: light ranker -> heavy ranker on top ~100
          5. store ranked ids as a session snapshot, return page 1
          6. hydrate: post cache, author cache, counters cache
```

- **Fan-out workers** consume `post_created`, read the follower list in pages of a few thousand and append to followers' feed lists in batches grouped by cache shard. They skip followers not active in 30 days; those feeds are rebuilt by pull when the user returns.
- **Feed service** merges push and pull candidates, applies filters, calls ranking with a strict deadline, and falls back to reverse-chronological order if ranking is slow or down.
- **Own posts**: the post service returns the new post and the client inserts it at the top; the feed service also merges the viewer's own latest posts, so read-your-writes holds without waiting for fan-out.

## Deep dives

### Fan-out on write, on read, or hybrid

| Model | Read cost | Write cost | Breaks on |
|-------|-----------|------------|-----------|
| Push (fan-out on write) | 1 cache read | followers x inserts per post | Celebrities: 100 M inserts, minutes of backlog |
| Pull (fan-out on read) | ~300 author timeline reads and a merge per load | 1 write | 175,000 loads/s x 300 reads = 50 M reads/s |
| Hybrid | 1 feed read + ~10-20 celebrity timeline reads | inserts for non-celebrity authors | Tuning the threshold |

Hybrid with a threshold around 500,000 followers: accounts above it are pulled at read time. Their author timelines are few and extremely hot, so they are replicated across cache nodes and held in each feed server's local memory for a few seconds. An account crossing the threshold changes path at the next post; no backfill is needed because pull reads the author timeline directly.

### Celebrity posts and hot keys

- A celebrity post is read by tens of millions within minutes. The post object and the author timeline are hot keys: replicate them, cache them in process, and use request coalescing so a cache miss produces one backend read per server.
- Counters on viral posts take thousands of increments per second: shard the counter (N sub-counters summed on read) and show approximate counts.

### Ranking and stable pagination

- Candidate generation (~500 from push and pull), a light ranker to trim to ~100, a heavy model on those; total budget about 100 ms of the 300 ms.
- Ranking changes as new posts arrive and engagement accrues, so offsets over a live ranking duplicate or skip posts. Instead, rank once per session, store the ranked id list (about 4 KB) as a snapshot with a 30-minute TTL, and page through it. New posts surface as "new posts available" on the next refresh, not by shifting pages.
- When the snapshot expires or is lost, the cursor falls back to "posts older than the last seen post id", which can repeat a ranked post but never skips a newer one; dedupe against ids the client already has.

### Cache tiers

| Tier | Holds | Notes |
|------|-------|-------|
| Client | Rendered feed, media | Offline reading, instant reopen |
| CDN | Media | Never feed responses (personalized) |
| Feed cache | Post id lists per user | The push side; largest memory cost |
| Author timeline cache | Recent post ids per author | Hot for celebrities |
| Object caches | Posts, users, counters | Hydration; >99% hit rate expected |

Lose a feed cache shard and its users get pull-built feeds (slower, rate limited) while the shard is rebuilt.

### Deletes, unfollows and blocks

- Filter at read time: hydration drops posts with `deleted_at`, the feed service drops authors not in the viewer's current `following` set (cached per user) and authors in the viewer's block list.
- Clean feed lists lazily, as entries age out of the 500-entry cap or in a background pass. Correctness comes from the filter, not the cleanup.

## Failure modes

| Failure | Effect | Mitigation |
|---------|--------|------------|
| Fan-out backlog (outage, viral event) | Posts appear late | Prioritize small authors' fan-out, autoscale workers, alert on post-to-feed lag; the 1-minute promise is what the backlog alert defends |
| Ranking service slow or down | Feed latency or errors | Deadline, then reverse-chronological fallback |
| Feed cache shard lost | Empty feeds for some users | Pull-based rebuild from author timelines with rate limiting |
| Hydration partially fails | Missing posts | Drop the failed items, return the page; never fail the whole feed |
| Follow graph shard slow | Fan-out stalls | Fan-out is asynchronous; retries with backoff, idempotent appends keyed by post id |

## Trade-offs

- **Write amplification versus read latency**: push makes reads one lookup at the cost of tens of billions of cache writes a day; the hybrid caps the worst case.
- **Memory versus compute**: precomputed feeds cost terabytes of RAM; restricting them to active users and 500 entries keeps the cost proportional to engagement.
- **Consistency**: feeds are eventually consistent (seconds); read-your-own-post is guaranteed by merging the author's own posts; deletes and unfollows are consistent at read time through filtering.
- **Stable pagination versus freshness**: snapshots freeze ranking for a session; freshness comes from refresh, not from shifting pages.

## Observability and cost

- Feed latency per stage (candidates, ranking, hydration), post-to-feed lag p50/p99 for normal and celebrity authors, fan-out queue depth, cache hit ratios per tier, ranking fallback rate, empty-feed rate, duplicate-in-session rate reported by clients; engagement metrics to catch silent quality regressions.
- Cost: feed cache RAM (about 8 TB with replicas) and fan-out compute dominate; ranking inference is the next line item. Lowering the 500-entry cap or the 30-day activity window are the main levers.

## Evolution

- Recommended content from outside the follow graph: more candidate sources feeding the same ranking stage.
- Ads insertion at fixed slots after ranking.
- Multi-region: feeds and caches regional, the follow graph and posts replicated globally; fan-out runs in the follower's home region.
- Edits: hydration reads the latest post version, so feed lists need no change.
