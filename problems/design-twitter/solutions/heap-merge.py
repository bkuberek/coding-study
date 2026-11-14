import heapq

FEED_SIZE = 10


class Twitter:
    def __init__(self) -> None:
        self.clock = 0
        # Each user's own tweets, oldest first, as (post time, tweet id).
        self.tweets: dict[int, list[tuple[int, int]]] = {}
        self.following: dict[int, set[int]] = {}

    def post_tweet(self, user_id: int, tweet_id: int) -> None:
        self.tweets.setdefault(user_id, []).append((self.clock, tweet_id))
        self.clock += 1

    def get_news_feed(self, user_id: int) -> list[int]:
        authors = self.following.get(user_id, set()) | {user_id}
        # One entry per author: (negated time, tweet id, author, index in their timeline).
        # heapq is a min-heap, so the negated time puts the newest tweet at the root.
        heap = []
        for author in authors:
            timeline = self.tweets.get(author)
            if timeline:
                time, tweet_id = timeline[-1]
                heap.append((-time, tweet_id, author, len(timeline) - 1))
        heapq.heapify(heap)
        feed: list[int] = []
        while heap and len(feed) < FEED_SIZE:
            _, tweet_id, author, index = heapq.heappop(heap)
            feed.append(tweet_id)
            if index > 0:
                time, older = self.tweets[author][index - 1]
                heapq.heappush(heap, (-time, older, author, index - 1))
        return feed

    def follow(self, follower_id: int, followee_id: int) -> None:
        if follower_id != followee_id:
            self.following.setdefault(follower_id, set()).add(followee_id)

    def unfollow(self, follower_id: int, followee_id: int) -> None:
        self.following.get(follower_id, set()).discard(followee_id)
