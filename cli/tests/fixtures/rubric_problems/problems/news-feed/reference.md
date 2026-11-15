# News Feed: Reference

## Requirements

Publish and read; reads dominate.

## Estimates

Billions of feed reads per day.

## API

`POST /posts`; `GET /feed?cursor=`.

## Data model

Posts by author; precomputed feed lists per user.

## High-level design

Fan-out workers push post ids into follower feeds; celebrity posts are merged at read time.

## Deep dives

The hybrid fan-out bounds write amplification.

## Trade-offs

Precomputed feeds cost storage but keep reads fast.
