# News Feed: Rubric

## Requirements and scope

- [ ] Identifies the core question: where to pay for the follower graph (write time, read time or both).
- [ ] Uses the 5-second versus 1-minute freshness split to justify a slower path for celebrity posts.
- [ ] Treats deletes, unfollows and blocks as read-time filters rather than synchronous writes to feeds.
- [ ] States read-your-own-post as a requirement and how it is met.
- [ ] Names what is out of scope (ads, recommendations, comments, media upload).

## Estimates

- [ ] Derives about 60,000 feed loads/s average and 2,000-7,000 posts/s.
- [ ] Computes fan-out on write at tens of billions of inserts per day and hundreds of thousands per second.
- [ ] Sizes the precomputed feed cache in terabytes and limits it (active users, capped list length).
- [ ] Quantifies why pure push fails for a 100-million-follower account and why pure pull fails at read volume.

## API and data model

- [ ] Defines publish, feed, follow and delete endpoints with an opaque cursor.
- [ ] Uses time-ordered post ids and explains what they buy.
- [ ] Stores the follow graph in both directions for fan-out and for read-time filtering.
- [ ] Models the feed cache, author timelines and counters as separate stores with different access patterns.

## High-level design

- [ ] Shows the asynchronous fan-out path (event log, workers paging through followers, batched appends).
- [ ] Shows the read path: candidates, merge with pulled celebrity posts, filter, rank, hydrate.
- [ ] Falls back to an unranked feed when ranking is slow or down.

## Deep dives

- [ ] Designs the hybrid with a follower threshold and explains how an account crossing it is handled.
- [ ] Handles hot keys for celebrity posts (replication, in-process caching, request coalescing) and hot counters (sharded, approximate).
- [ ] Solves stable pagination over a changing ranking (session snapshot or equivalent), not offsets.
- [ ] Lays out cache tiers and what is and is not cacheable (feed responses are personalized; media is not).
- [ ] Skips fan-out to inactive users and rebuilds their feed by pull on return.

## Failure modes and trade-offs

- [ ] Handles a fan-out backlog with prioritization and lag alerting tied to the freshness promise.
- [ ] Handles loss of a feed cache shard by rebuilding from author timelines.
- [ ] Degrades gracefully on partial hydration failures.
- [ ] States the consistency model: eventual for feeds, read-your-writes for own posts, filters for deletes.
- [ ] Discusses write amplification versus read latency and memory versus compute.

## Operations and evolution

- [ ] Names the key metrics: post-to-feed lag, per-stage feed latency, ranking fallback rate, cache hit ratios, empty-feed rate.
- [ ] Identifies feed cache memory and fan-out compute as the dominant costs and the levers that reduce them.
- [ ] Describes how recommendations, ads or multi-region deployment would change the design.
