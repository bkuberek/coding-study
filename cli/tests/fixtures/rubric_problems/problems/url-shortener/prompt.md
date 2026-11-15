# URL Shortener

## Question

Design a service that turns long URLs into short links and redirects visitors from a short link to the original URL.

## Functional requirements

- Create a short link for a long URL, optionally with a custom alias.
- Redirect a short link to its long URL.
- Links expire after an optional time to live.

## Non-functional requirements

- Redirects are fast (p99 under 50 ms) and highly available.
- Short links are not guessable in sequence.

## Scale

- 100 million new links per month.
- 100 redirects for every link created.
