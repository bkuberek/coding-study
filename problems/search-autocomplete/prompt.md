# Search Autocomplete

## Question

Design the typeahead behind the search box of a large online marketplace. As a shopper types, the box shows up to 10 suggested queries for the text typed so far; picking one runs that search.

## Functional requirements

- Return up to 10 suggestions for a prefix, ranked mostly by how often shoppers search for them, with recent popularity weighted more than old.
- Trending queries (a product launch, a news event) start appearing within 15 minutes.
- Never suggest offensive or legally blocked terms; an urgent removal takes effect within 5 minutes.
- Light personalization: a signed-in shopper's own recent searches that match the prefix are shown first.
- One index per locale (for example `en-US`, `de-DE`); queries are matched case- and accent-insensitively.

## Non-functional requirements

- Suggestions must appear before the next keystroke: p99 under 150 ms end to end, under 20 ms inside the service.
- 99.95% availability; when autocomplete is down, search itself keeps working.
- Suggestions may be slightly stale (minutes) but must be consistent across a session: the list should not flicker between index versions while the shopper types.

## Scale

- 100 million daily active shoppers, 10 searches each per day.
- Clients wait 100 ms after the last keystroke before asking, which leaves about 6 requests per search.
- Peak traffic is 3 times the average.
- The query log holds about 1 billion searches per day; about 50 million distinct queries per locale are worth suggesting.
