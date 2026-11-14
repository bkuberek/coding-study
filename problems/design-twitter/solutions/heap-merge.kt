import java.util.PriorityQueue

private const val FEED_SIZE = 10

class Twitter {
    private class Tweet(val time: Int, val tweetId: Int)

    private class Cursor(val tweet: Tweet, val author: Int, val index: Int)

    private var clock = 0
    // Each user's own tweets, oldest first.
    private val tweets = HashMap<Int, MutableList<Tweet>>()
    private val following = HashMap<Int, MutableSet<Int>>()

    fun postTweet(userId: Int, tweetId: Int) {
        tweets.getOrPut(userId) { ArrayList() }.add(Tweet(clock++, tweetId))
    }

    fun getNewsFeed(userId: Int): List<Int> {
        val authors = following[userId].orEmpty() + userId
        // The newest tweet among the authors' cursors is at the head.
        val heap = PriorityQueue<Cursor>(compareByDescending { it.tweet.time })
        for (author in authors) {
            val timeline = tweets[author] ?: continue
            if (timeline.isNotEmpty()) heap.offer(Cursor(timeline.last(), author, timeline.lastIndex))
        }
        val feed = ArrayList<Int>()
        while (heap.isNotEmpty() && feed.size < FEED_SIZE) {
            val newest = heap.poll()
            feed.add(newest.tweet.tweetId)
            if (newest.index > 0) {
                val older = newest.index - 1
                heap.offer(Cursor(tweets.getValue(newest.author)[older], newest.author, older))
            }
        }
        return feed
    }

    fun follow(followerId: Int, followeeId: Int) {
        if (followerId != followeeId) following.getOrPut(followerId) { HashSet() }.add(followeeId)
    }

    fun unfollow(followerId: Int, followeeId: Int) {
        following[followerId]?.remove(followeeId)
    }
}
