# Search Autocomplete: Notes

## Requirements

<!-- Read path versus pipeline, freshness needs, removals, personalization scope, session consistency. -->

## Estimates

<!-- Requests per second from searches and keystrokes, index size per locale, serving fleet size. -->

## API

<!-- Suggest endpoint, caching headers, index version, client behavior. -->

## Data model

<!-- Query log, aggregates, index snapshot layout, trending overlay, blocklist, recent searches. -->

## High-level design

<!-- Client, CDN, suggest service, batch build, streaming trending job, snapshot distribution. -->

## Deep dives

<!-- Index structure; ranking and normalization; freshness; latency budget; rollout and consistency. -->

## Failure modes

<!-- Bad builds, lagging pipelines, manipulation, service outage. -->

## Trade-offs

<!-- Replicate or shard, precompute or compute, cacheability or personalization. -->

## Observability and cost

<!-- Latency, cache hit rate, quality metrics, snapshot ages; fleet and batch cost. -->

## Evolution

<!-- Typo tolerance, rich suggestions, learned ranking, more locales. -->
