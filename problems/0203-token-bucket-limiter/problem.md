# Token Bucket Limiter

## Statement

A token bucket limits how fast clients may use a service while still allowing short bursts. The bucket holds up to `capacity` tokens and gains `refillPerSecond` tokens for every second that passes, never more than `capacity`. A request that costs `n` tokens is allowed only if the bucket holds at least `n`, and then takes them. Many request threads share one bucket, so the counting must stay exact under concurrency: never grant a token that was not earned, and never lose one.

Time is passed in explicitly, so the bucket never reads a clock. Implement the class `TokenBucket`:

- `TokenBucket(capacity, refillPerSecond)` creates a full bucket: it holds `capacity` tokens as of timestamp 0.
- `tryAcquire(timestamp, tokens)` first refills the bucket up to `timestamp`, then takes `tokens` tokens if the bucket holds at least that many. It returns whether it took them; a request that cannot be served in full takes nothing.
- `available(timestamp)` refills the bucket up to `timestamp` and returns how many tokens it holds.

Refilling up to timestamp `t`: if `t` is later than the latest timestamp the bucket has refilled to so far, add `(t - latest) * refillPerSecond` tokens, capped at `capacity`, and remember `t` as the latest. If `t` is not later, add nothing: concurrent callers may arrive slightly out of order, and time never runs backwards for the bucket.

## Input

- Constructor `capacity`: the most tokens the bucket holds; `refillPerSecond`: the tokens added per second.
- `tryAcquire(timestamp, tokens)`: the current time in seconds and the cost of the request.
- `available(timestamp)`: the current time in seconds.

Sequential tests are a sequence of calls on one worker: the constructor first, then method calls in order. Stress tests call the same methods from many workers at once.

## Output

- `tryAcquire` returns `true` when it took the tokens and `false` otherwise.
- `available` returns the number of tokens in the bucket after refilling.

The expected output of a sequential test lists one result per call, with `null` for the constructor.

## Examples

### Example 1

<!-- case: ex1 -->

The full bucket of 5 serves requests of 3 and 2 at timestamp 0. Nothing is left for a third request, because no time has passed.

### Example 2

<!-- case: ex2 -->

The bucket is emptied at second 1. Two seconds later it has earned 4 tokens; much later it is full again at 10, not more, and a request of 7 leaves 3.

## Constraints

- `1 <= capacity <= 10^12`
- `0 <= refillPerSecond <= 10^6`
- `0 <= timestamp <= 10^9`
- `1 <= tokens <= 10^12`

## Concurrency

`tryAcquire` and `available` are called concurrently by many workers, with timestamps that may arrive slightly out of order. Neither method waits for anything but a lock.

- Exactness: every token is either still in the bucket or taken by exactly one granted request. Over a whole run, the tokens granted plus the tokens left equal the capacity plus everything refilled up to the latest timestamp; the stress tests check this sum after every run.
- The same elapsed time is never counted twice, so two workers that refill at the same moment add tokens once.
- The bucket never holds a negative number of tokens, and no request is granted unless the bucket held its full cost at that moment.

Java and Kotlin run on platform threads and on virtual threads, and Python on threads. A passing stress run is evidence of correct synchronization, not proof.

## Follow-ups

- How would you support fractional refill rates, such as 1 token every 400 milliseconds, without drifting?
- How would you make `tryAcquire` wait for enough tokens instead of failing, without letting small requests starve a large one?
- How would the design change for a limiter shared by many servers?

## Hints

### Hint 1

Refill lazily: store the token count and the timestamp of the latest refill, and catch up only when someone asks.

### Hint 2

Refill, check and take must be one atomic step. Two workers that both read "the latest refill was at 7" both add the tokens for the same seconds.

### Hint 3

One lock around the whole method is enough. Without a lock, an immutable (tokens, latest) pair in an atomic reference updated with compare-and-set works too.
