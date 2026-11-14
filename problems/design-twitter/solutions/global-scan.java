import java.util.*;

public class Twitter {
    private static final int FEED_SIZE = 10;

    // Every tweet ever posted, oldest first, as {author, tweet id}.
    private final List<int[]> timeline = new ArrayList<>();
    private final Map<Integer, Set<Integer>> following = new HashMap<>();

    public Twitter() {
    }

    public void postTweet(int userId, int tweetId) {
        timeline.add(new int[] {userId, tweetId});
    }

    public List<Integer> getNewsFeed(int userId) {
        Set<Integer> followees = following.getOrDefault(userId, Set.of());
        List<Integer> feed = new ArrayList<>();
        for (int index = timeline.size() - 1; index >= 0 && feed.size() < FEED_SIZE; index--) {
            int[] tweet = timeline.get(index);
            if (tweet[0] == userId || followees.contains(tweet[0])) {
                feed.add(tweet[1]);
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
}
