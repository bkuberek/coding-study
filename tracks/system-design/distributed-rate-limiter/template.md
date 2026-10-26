# Distributed Rate Limiter: Notes

## Requirements

<!-- Purposes of the limits, failure policy per rule, accuracy budget, rule shapes, where the check runs. -->

## Estimates

<!-- Checks per second, counter-store calls and shards, memory, latency budget versus round trips. -->

## API

<!-- The check call, response headers and status codes, the operator API for rules and overrides. -->

## Data model

<!-- Rules, overrides, counter keys and TTLs; how a subject's counters stay on one shard. -->

## High-level design

<!-- Gateway, limiter library or service, counter store, rule distribution, decision logging. -->

## Deep dives

<!-- Algorithm choice; atomicity and time; hot keys; global quotas across regions. -->

## Failure modes

<!-- Store down or slow, rules service down, bad rule rollout. -->

## Trade-offs

<!-- Accuracy versus latency, fail open versus closed, library versus service, regional versus global. -->

## Observability and cost

<!-- Metrics, debugging rejections, what the system costs. -->

## Evolution

<!-- Concurrency limits, cost-weighted limits, adaptive shedding, billing. -->
