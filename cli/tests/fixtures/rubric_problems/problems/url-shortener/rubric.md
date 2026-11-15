# URL Shortener: Rubric

## Requirements and estimates

- [ ] Separates the write path (create) from the read path (redirect) and notes the 100:1 ratio.
- [ ] Estimates storage for five years of links.

## Design

- [ ] Picks a key scheme (counter with base62, hash with collision handling, or pre-generated keys) and explains the trade-off.
- [ ] Caches hot links in front of the store.

## Operations

- [ ] Handles expiry without scanning the whole table.
