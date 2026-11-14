const FEED_SIZE = 10;

export class Twitter {
  // Every tweet ever posted, oldest first, as [author, tweet id].
  private readonly timeline: [number, number][] = [];
  private readonly following = new Map<number, Set<number>>();

  postTweet(userId: number, tweetId: number): void {
    this.timeline.push([userId, tweetId]);
  }

  getNewsFeed(userId: number): number[] {
    const followees = this.following.get(userId);
    const feed: number[] = [];
    for (let index = this.timeline.length - 1; index >= 0 && feed.length < FEED_SIZE; index--) {
      const [author, tweetId] = this.timeline[index];
      if (author === userId || followees?.has(author)) {
        feed.push(tweetId);
      }
    }
    return feed;
  }

  follow(followerId: number, followeeId: number): void {
    if (followerId === followeeId) {
      return;
    }
    let followees = this.following.get(followerId);
    if (followees === undefined) {
      followees = new Set();
      this.following.set(followerId, followees);
    }
    followees.add(followeeId);
  }

  unfollow(followerId: number, followeeId: number): void {
    this.following.get(followerId)?.delete(followeeId);
  }
}
