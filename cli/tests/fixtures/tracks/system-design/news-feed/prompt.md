# News Feed

## Question

Design the home feed of a social network: each user sees recent posts from the accounts they follow.

## Functional requirements

- Publish a post.
- Read the feed, newest first, paginated.

## Non-functional requirements

- Feed reads under 200 ms at p99.

## Scale

- 300 million daily active users; a few accounts have tens of millions of followers.
