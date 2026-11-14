package design_twitter

const feedSize = 10

// tweet is one entry of the global timeline.
type tweet struct {
	author, id int
}

type Twitter struct {
	// timeline holds every tweet ever posted, oldest first.
	timeline  []tweet
	following map[int]map[int]struct{}
}

func NewTwitter() *Twitter {
	return &Twitter{following: make(map[int]map[int]struct{})}
}

func (t *Twitter) PostTweet(userId int, tweetId int) {
	t.timeline = append(t.timeline, tweet{userId, tweetId})
}

func (t *Twitter) GetNewsFeed(userId int) []int {
	followees := t.following[userId]
	feed := make([]int, 0, feedSize)
	for i := len(t.timeline) - 1; i >= 0 && len(feed) < feedSize; i-- {
		entry := t.timeline[i]
		_, follows := followees[entry.author]
		if entry.author == userId || follows {
			feed = append(feed, entry.id)
		}
	}
	return feed
}

func (t *Twitter) Follow(followerId int, followeeId int) {
	if followerId == followeeId {
		return
	}
	if t.following[followerId] == nil {
		t.following[followerId] = make(map[int]struct{})
	}
	t.following[followerId][followeeId] = struct{}{}
}

func (t *Twitter) Unfollow(followerId int, followeeId int) {
	delete(t.following[followerId], followeeId)
}
