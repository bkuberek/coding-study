# Mini Twitter: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| global-scan | brute | O(T) per getNewsFeed, O(1) otherwise | O(T + F) | few tweets, or as a reference implementation |
| heap-merge | optimal | O(f + 10 log f) per getNewsFeed, O(1) otherwise | O(T + F) | default answer |

`T` is the number of tweets posted so far, `F` the number of follow relations, and `f` the number of people the reader follows. Both designs keep a set of followees per user, so `follow` and `unfollow` are O(1) on average; they differ in how tweets are stored and how a feed is assembled.

## Approach: global-scan (One global timeline, scanned from the newest tweet)

### Intuition

Keep every tweet in one list in posting order. A feed is the newest tweets in that list whose author is the reader or someone the reader follows: walk the list from its end and collect matches until there are 10.

### Algorithm

1. `postTweet`: append `(userId, tweetId)` to the global list.
2. `getNewsFeed(userId)`: walk the list from newest to oldest; collect each tweet whose author is `userId` or one of their followees; stop at 10 or at the start of the list.
3. `follow`: unless follower and followee are the same, add the followee to the follower's set.
4. `unfollow`: remove the followee from the follower's set, if present.

### Correctness

The global list is in posting order, so walking it backwards visits tweets from newest to oldest. The filter keeps exactly the tweets the reader may see under the current follow sets, and stopping after 10 matches yields the 10 most recent visible tweets, newest first. Ignoring self-follows keeps the follow sets free of the reader, which is harmless here and matters for the heap design.

### Complexity

- Time: O(T) per getNewsFeed, O(1) otherwise — a reader who follows few active users may need to walk the whole timeline, and an inactive reader always does. In the generated sequences, a quarter of the feed requests come from users who never post or follow, so the total cost grows with the square of the number of calls.
- Space: O(T + F) — every tweet once, plus the follow sets.

### Trade-offs

Very little code and obviously correct, which makes it the oracle. Posting is as cheap as it gets. Reading is the problem: the work depends on the whole network's activity, not on the reader's own connections.

### Pitfalls and edge cases

- An unknown reader must get an empty feed, not an error: use a default empty set.
- Tweet ids are not timestamps; never sort by id.

### Language notes

- Python: `self.following.get(user_id, set())` reads without creating an entry; `setdefault` creates one only when following.
- TypeScript: `followees?.has(author)` handles a reader with no follow set.
- Java: `Set.of()` is an immutable empty default for `getOrDefault`.
- Kotlin: `following[userId].orEmpty()` turns a missing set into an empty one, and destructuring `val (author, tweetId)` reads a `Pair`.

## Approach: heap-merge (Per-user timelines merged with a max-heap)

### Intuition

A reader's feed only ever involves the reader and their followees. Store each user's tweets in their own list, stamped with a global counter. Each of those lists is already sorted by time, so the feed is the first 10 elements of a merge of `f + 1` sorted lists, read from their newest ends: exactly what a max-heap of one cursor per list does, stopping after 10 pops.

### Algorithm

1. `postTweet`: append `(clock, tweetId)` to the author's own list and increase `clock`.
2. `getNewsFeed(userId)`:
   1. For the reader and each followee with at least one tweet, push a cursor on their newest tweet into a max-heap ordered by timestamp.
   2. Pop the newest cursor, add its tweet to the feed, and push a cursor on the next older tweet of the same author, if any.
   3. Stop after 10 tweets or when the heap is empty.
3. `follow` and `unfollow`: as in the global scan; self-follows are ignored so the reader's timeline is never merged twice.

### Correctness

The heap always holds, for every visible author with unread tweets, a cursor on that author's newest unread tweet. The newest unread visible tweet overall is the newest among those cursors, which is the heap's root, so the pops come out in non-increasing time order without skipping any visible tweet. Advancing the popped cursor to the same author's next older tweet restores the invariant. The first 10 pops are therefore the 10 most recent visible tweets.

### Complexity

- Time: O(f + 10 log f) per getNewsFeed, O(1) otherwise — building the heap of at most `f + 1` cursors is linear (or O(f log f) with repeated pushes), and at most 10 pops and 10 pushes follow. Posting and following are O(1) on average.
- Space: O(T + F) — each tweet is stored once, in its author's list; the heap is temporary.

### Trade-offs

Reading costs depend only on the reader's own connections, which is the property a real feed service needs. Each user's list could be capped at the 10 newest tweets, since no feed ever reaches further back into one timeline. At real scale the trade-off becomes fan-out on write (push tweets into followers' feeds at post time) versus fan-out on read (this merge), usually mixed for celebrity accounts.

### Pitfalls and edge cases

- A self-follow stored in the set would merge the reader's own timeline twice and duplicate tweets; ignore it.
- Skip authors with no tweets when filling the heap; an empty list has no newest tweet.
- Order the heap by timestamp, never by tweet id.

### Language notes

- Python: `heapq` is a min-heap, so cursors store the negated timestamp; `heapify` builds the heap from the initial cursors in linear time. The tuple's later fields are never compared, because timestamps are unique.
- TypeScript: no built-in priority queue, so the reference implements a small max-heap of cursor objects; object spread copies a tweet's fields into a new cursor.
- Java: cursors are `int[] {time, tweetId, author, index}` in a `PriorityQueue` with a reversed comparator; `getNewsFeed` returns a `List<Integer>`, as the `list<int>` signature requires.
- Kotlin: small private classes for tweets and cursors read better than arrays; `following[userId].orEmpty() + userId` builds the author set in one expression, and `compareByDescending { it.tweet.time }` makes the max-heap.
