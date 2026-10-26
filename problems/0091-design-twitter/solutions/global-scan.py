FEED_SIZE = 10


class Twitter:
    def __init__(self) -> None:
        # Every tweet ever posted, oldest first, as (author, tweet id).
        self.timeline: list[tuple[int, int]] = []
        self.following: dict[int, set[int]] = {}

    def post_tweet(self, user_id: int, tweet_id: int) -> None:
        self.timeline.append((user_id, tweet_id))

    def get_news_feed(self, user_id: int) -> list[int]:
        followees = self.following.get(user_id, set())
        feed: list[int] = []
        for author, tweet_id in reversed(self.timeline):
            if author == user_id or author in followees:
                feed.append(tweet_id)
                if len(feed) == FEED_SIZE:
                    break
        return feed

    def follow(self, follower_id: int, followee_id: int) -> None:
        if follower_id != followee_id:
            self.following.setdefault(follower_id, set()).add(followee_id)

    def unfollow(self, follower_id: int, followee_id: int) -> None:
        self.following.get(follower_id, set()).discard(followee_id)
