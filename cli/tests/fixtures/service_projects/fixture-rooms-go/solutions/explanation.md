# Rooms in Go: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | Always |

## Approach: reference (Reference)

### Intuition

The stock lives in the data folder, so a fresh start restores it; the vendor is a call that can fail.

### Algorithm

1. Read the stock on each request.
2. Call the vendor with a timeout, and retry once after a 429.

### Design

- `main.go`: the routes, the stock and the vendor call.
- A cache of the vendor's answer and a circuit breaker cannot be graded over HTTP: they belong here.

### Correctness

Every failure of the vendor answers no rooms and says it is degraded.

### Complexity

- Time: per request — one or two vendor calls
- Space: per request — the vendor's answer

### Trade-offs

A retry makes a slow answer slower, which the 1 second limit bounds.

### Pitfalls and edge cases

A 200 can still carry a body that is not JSON.
