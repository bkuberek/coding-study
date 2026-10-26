# URL Shortener: Reference

## Requirements

Create, redirect and expire links; redirects dominate traffic.

## Estimates

About 40 writes and 4000 reads per second on average; 6 billion links over five years.

## API

`POST /links {url, alias?, ttl?}` returns the short code; `GET /{code}` answers 301 or 302.

## Data model

One table keyed by code: long URL, owner, created and expiry times.

## High-level design

Stateless API servers, a key-value store, a cache for hot codes and a key generation service.

## Deep dives

Pre-generated random keys avoid coordination on the write path and keep codes unguessable.

## Trade-offs

A 302 redirect keeps analytics accurate at the cost of more redirect traffic than a 301.
