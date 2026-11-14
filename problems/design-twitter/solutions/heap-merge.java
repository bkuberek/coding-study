import java.util.*;

public class Twitter {
    private static final int FEED_SIZE = 10;

    private int clock = 0;
    // Each user's own tweets, oldest first, as {post time, tweet id}.
    private final Map<Integer, List<int[]>> tweets = new HashMap<>();
    private final Map<Integer, Set<Integer>> following = new HashMap<>();

    public Twitter() {
    }

    public void postTweet(int userId, int tweetId) {
        tweets.computeIfAbsent(userId, id -> new ArrayList<>()).add(new int[] {clock++, tweetId});
    }

    public List<Integer> getNewsFeed(int userId) {
        Set<Integer> authors = new HashSet<>(following.getOrDefault(userId, Set.of()));
        authors.add(userId);
        // Cursors are {post time, tweet id, author, index}; the newest tweet is at the head.
        PriorityQueue<int[]> heap = new PriorityQueue<>((a, b) -> Integer.compare(b[0], a[0]));
        for (int author : authors) {
            List<int[]> timeline = tweets.get(author);
            if (timeline != null && !timeline.isEmpty()) {
                heap.offer(cursor(timeline, author, timeline.size() - 1));
            }
        }
        List<Integer> feed = new ArrayList<>();
        while (!heap.isEmpty() && feed.size() < FEED_SIZE) {
            int[] newest = heap.poll();
            feed.add(newest[1]);
            if (newest[3] > 0) {
                heap.offer(cursor(tweets.get(newest[2]), newest[2], newest[3] - 1));
            }
        }
        return feed;
    }

    public void follow(int followerId, int followeeId) {
        if (followerId != followeeId) {
            following.computeIfAbsent(followerId, id -> new HashSet<>()).add(followeeId);
        }
    }

    public void unfollow(int followerId, int followeeId) {
        Set<Integer> followees = following.get(followerId);
        if (followees != null) {
            followees.remove(followeeId);
        }
    }

    private static int[] cursor(List<int[]> timeline, int author, int index) {
        int[] tweet = timeline.get(index);
        return new int[] {tweet[0], tweet[1], author, index};
    }
}
