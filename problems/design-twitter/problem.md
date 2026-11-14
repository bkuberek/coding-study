# Mini Twitter

## Statement

Build the core of a tiny social network. Users post short messages ("tweets"), follow and unfollow each other, and read a news feed of recent tweets. Implement the class `Twitter`:

- `Twitter()` creates an empty network: no users, no tweets, no follows.
- `postTweet(userId, tweetId)` records that user `userId` posted a new tweet with id `tweetId`. Every call uses a tweet id that was never used before.
- `getNewsFeed(userId)` returns the ids of the **10 most recent** tweets that user `userId` can see, newest first. A user sees their own tweets and the tweets of everyone they currently follow, including tweets posted before the follow began. If fewer than 10 such tweets exist, return all of them.
- `follow(followerId, followeeId)` makes `followerId` follow `followeeId`. Following someone you already follow, or yourself, changes nothing.
- `unfollow(followerId, followeeId)` ends that follow. Unfollowing someone you do not follow, or yourself, changes nothing.

Recency is the order of the `postTweet` calls; tweet ids are labels and say nothing about time. A user exists as soon as any call mentions them.

Reference: this is our own wording of LeetCode problem 355, [Design Twitter](https://leetcode.com/problems/design-twitter/).

## Input

- Constructor: no arguments.
- `postTweet(userId, tweetId)`: the author and the new tweet's id.
- `getNewsFeed(userId)`: the reader.
- `follow(followerId, followeeId)` and `unfollow(followerId, followeeId)`: who starts or stops following whom.

Each test is a sequence of calls: the constructor first, then the methods in order.

## Output

- `getNewsFeed` returns a list of at most 10 tweet ids, newest first.
- The constructor, `postTweet`, `follow` and `unfollow` return nothing.

The expected output of a test lists one result per call, with `null` for calls that return nothing.

## Examples

### Example 1

<!-- case: ex1 -->

User 1 follows user 2, so the first feed shows user 1's own tweet 102 and user 2's tweet 101, newest first; user 3's tweet 103 is not visible yet. After following user 3 as well, all three timelines are merged by recency: 103, 102, 101. After unfollowing user 2, tweet 101 disappears again.

### Example 2

<!-- case: ex2 -->

User 3 posted twelve tweets, but the feed holds only the ten most recent: 511 down to 502.

## Constraints

- `1 <= userId, followerId, followeeId <= 1000`
- `0 <= tweetId <= 10^6`, and every `postTweet` uses a new `tweetId`.
- At most `3 * 10^4` calls in total.

## Follow-ups

- Scanning all tweets ever posted for every feed request is simple. When does it become slow?
- Each user's own tweets are already in time order. How can you combine several such sorted timelines and stop after 10 tweets?
- How would the design change for millions of users, where a celebrity has millions of followers?

## Hints

### Hint 1

Keep a set of followees per user, and give every tweet a global, increasing timestamp when it is posted.

### Hint 2

Store each user's tweets in their own list. Their newest tweet is at the end, so each followee's timeline is a sorted list you read backwards.

### Hint 3

Merging the timelines is the "merge k sorted lists" problem: put each timeline's newest tweet into a max-heap keyed by timestamp, pop the newest, and push the next older tweet from the same timeline. Stop after 10 pops.
