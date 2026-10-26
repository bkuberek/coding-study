const FEED_SIZE = 10;

type Tweet = { time: number; tweetId: number };
type Cursor = { time: number; tweetId: number; author: number; index: number };

// A binary max-heap of cursors ordered by post time: TypeScript has no priority queue.
class CursorHeap {
  private readonly items: Cursor[] = [];

  get size(): number {
    return this.items.length;
  }

  push(cursor: Cursor): void {
    const items = this.items;
    items.push(cursor);
    let child = items.length - 1;
    while (child > 0) {
      const parent = (child - 1) >> 1;
      if (items[parent].time >= items[child].time) {
        break;
      }
      [items[parent], items[child]] = [items[child], items[parent]];
      child = parent;
    }
  }

  pop(): Cursor {
    const items = this.items;
    const top = items[0];
    const last = items.pop()!;
    if (items.length > 0) {
      items[0] = last;
      let parent = 0;
      for (;;) {
        const left = 2 * parent + 1;
        const right = left + 1;
        let newest = parent;
        if (left < items.length && items[left].time > items[newest].time) {
          newest = left;
        }
        if (right < items.length && items[right].time > items[newest].time) {
          newest = right;
        }
        if (newest === parent) {
          break;
        }
        [items[parent], items[newest]] = [items[newest], items[parent]];
        parent = newest;
      }
    }
    return top;
  }
}

export class Twitter {
  private clock = 0;
  // Each user's own tweets, oldest first.
  private readonly tweets = new Map<number, Tweet[]>();
  private readonly following = new Map<number, Set<number>>();

  postTweet(userId: number, tweetId: number): void {
    let timeline = this.tweets.get(userId);
    if (timeline === undefined) {
      timeline = [];
      this.tweets.set(userId, timeline);
    }
    timeline.push({ time: this.clock++, tweetId });
  }

  getNewsFeed(userId: number): number[] {
    const authors = new Set(this.following.get(userId));
    authors.add(userId);
    const heap = new CursorHeap();
    for (const author of authors) {
      const timeline = this.tweets.get(author);
      if (timeline !== undefined && timeline.length > 0) {
        const index = timeline.length - 1;
        heap.push({ ...timeline[index], author, index });
      }
    }
    const feed: number[] = [];
    while (heap.size > 0 && feed.length < FEED_SIZE) {
      const { tweetId, author, index } = heap.pop();
      feed.push(tweetId);
      if (index > 0) {
        heap.push({ ...this.tweets.get(author)![index - 1], author, index: index - 1 });
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
