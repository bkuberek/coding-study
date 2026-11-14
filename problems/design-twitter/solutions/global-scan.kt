private const val FEED_SIZE = 10

class Twitter {
    // Every tweet ever posted, oldest first, as (author, tweet id).
    private val timeline = ArrayList<Pair<Int, Int>>()
    private val following = HashMap<Int, MutableSet<Int>>()

    fun postTweet(userId: Int, tweetId: Int) {
        timeline.add(userId to tweetId)
    }

    fun getNewsFeed(userId: Int): List<Int> {
        val followees = following[userId].orEmpty()
        val feed = ArrayList<Int>()
        for (index in timeline.indices.reversed()) {
            val (author, tweetId) = timeline[index]
            if (author == userId || author in followees) {
                feed.add(tweetId)
                if (feed.size == FEED_SIZE) break
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
