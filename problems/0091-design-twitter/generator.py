"""Seeded operation sequences for design-twitter.

`n` is the number of calls after the constructor. There are A = n / 20 active users (between
2 and 500) and A / 4 quiet users (at least 1) whose ids follow the active ones. Active users
post (40% of calls), read their feed (30%), follow (20%) and unfollow (10%); a followee may be
the follower itself, which must be a no-op. A quarter of the feed reads come from quiet users,
who never post or follow: their feed is always empty, and a solution that scans one global
timeline reads every tweet to find that out, which makes it quadratic. Tweet ids are distinct
and in random order, so they say nothing about recency.
"""

import random

MAX_CALLS = 3 * 10**4
MAX_USER_ID = 1000
MAX_TWEET_ID = 10**6
MAX_ACTIVE = 500
USERS_PER_CALL = 20
CALL_WEIGHTS = (("postTweet", 0.4), ("getNewsFeed", 0.3), ("follow", 0.2), ("unfollow", 0.1))
QUIET_FEED_SHARE = 0.25
ARITY = {"postTweet": 2, "getNewsFeed": 1, "follow": 2, "unfollow": 2}


def generate(rng: random.Random, n: int) -> dict:
    calls = min(max(n, 1), MAX_CALLS)
    active = min(max(2, calls // USERS_PER_CALL), MAX_ACTIVE)
    quiet = max(1, active // 4)
    tweet_ids = rng.sample(range(MAX_TWEET_ID + 1), calls)
    names = [name for name, _ in CALL_WEIGHTS]
    weights = [weight for _, weight in CALL_WEIGHTS]
    ops: list[str] = ["Twitter"]
    args: list[list[int]] = [[]]
    for call in range(calls):
        op = rng.choices(names, weights)[0]
        user = rng.randint(1, active)
        ops.append(op)
        if op == "postTweet":
            args.append([user, tweet_ids[call]])
        elif op == "getNewsFeed":
            if rng.random() < QUIET_FEED_SHARE:
                user = rng.randint(active + 1, active + quiet)
            args.append([user])
        else:
            args.append([user, rng.randint(1, active)])
    return {"ops": ops, "args": args}


def validate(case_input: dict) -> None:
    ops, args = case_input["ops"], case_input["args"]
    assert len(ops) == len(args), "ops and args differ in length"
    assert ops[0] == "Twitter" and args[0] == [], "the first op must be the constructor"
    assert len(ops) - 1 <= MAX_CALLS, "too many calls"
    seen_tweets: set[int] = set()
    for op, arguments in zip(ops[1:], args[1:], strict=True):
        assert ARITY.get(op) == len(arguments), f"bad call {op}{arguments}"
        users = arguments[:1] if op in ("postTweet", "getNewsFeed") else arguments
        assert all(1 <= user <= MAX_USER_ID for user in users), "user id out of range"
        if op == "postTweet":
            tweet = arguments[1]
            assert 0 <= tweet <= MAX_TWEET_ID, "tweet id out of range"
            assert tweet not in seen_tweets, "tweet ids must be distinct"
            seen_tweets.add(tweet)
