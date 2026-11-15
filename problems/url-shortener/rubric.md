# URL Shortener: Rubric

## Requirements and scope

- [ ] Separates the create path from the redirect path and treats redirect availability and latency as the primary goal.
- [ ] States that codes are never reused and destinations never change, and uses that write-once property to justify caching and asynchronous replication.
- [ ] Asks about or states analytics freshness and loss tolerance before choosing the pipeline.
- [ ] Names what is out of scope (editing destinations, custom domains) instead of silently ignoring it.

## Estimates

- [ ] Derives roughly 80 creates/s and 8,000 redirects/s on average, and 5 times that at peak.
- [ ] Sizes storage for 12 billion links (single-digit terabytes per copy) and concludes storage is not the hard part.
- [ ] Justifies the code length from the key space (7 versus 8 characters) in terms of collisions and guessability.
- [ ] Sizes the hot cache and shows it fits in memory.

## API and data model

- [ ] Defines create, redirect, disable, list and stats endpoints with status codes (404 versus 410, 409 for a taken alias).
- [ ] Chooses 302 or 307 over 301 and explains the effect on analytics and on disabling links.
- [ ] Makes create idempotent with an idempotency key.
- [ ] Keys the link store by code with a conditional insert, and adds an owner index for listing.

## High-level design

- [ ] Draws stateless redirect servers, a cache tier and a key-value store, deployed in every region.
- [ ] Keeps analytics out of the synchronous redirect path (buffer, log, stream aggregation).
- [ ] Includes abuse handling: URL scanning at create, rate limits on creates and on 404s.

## Deep dives

- [ ] Compares at least three code-generation schemes and picks one with a reason (random plus conditional insert, counter plus permutation, or a key pool).
- [ ] Handles skew: in-process cache for the hottest links, single-flight on misses, negative caching for unknown codes.
- [ ] Explains why custom aliases need a single point of uniqueness across regions (last-writer-wins replication would grant one alias twice).
- [ ] Handles read-after-create across regions (fallback to the primary on a miss before returning 404).
- [ ] Makes a disable take effect within the 1-minute requirement (invalidation fan-out plus bounded TTLs).
- [ ] Gets exact click counts from at-least-once delivery plus deduplication, and filters bots and link previews.

## Failure modes and trade-offs

- [ ] Explains what happens when the cache tier fails and how the store or load shedding absorbs it.
- [ ] Explains what happens when the event log is down (redirects unaffected, events buffered or spilled to disk).
- [ ] States the consistency model of each path: strong for creates, eventual for redirects, and why that is safe.
- [ ] Discusses caching redirects at the CDN and what it costs in analytics and disable latency.

## Operations and evolution

- [ ] Names the key metrics: redirect p99 per region, cache hit ratio, 404 rate, analytics lag, disable propagation time.
- [ ] Identifies the main cost drivers (always-on redirect fleet, analytics storage) rather than link storage.
- [ ] Describes how custom domains or editable destinations would change the design.
