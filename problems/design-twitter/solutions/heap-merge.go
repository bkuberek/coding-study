package design_twitter

import "container/heap"

const feedSize = 10

// post is one tweet of a user's own timeline.
type post struct {
	time, id int
}

// cursor points at one tweet of one author's timeline.
type cursor struct {
	time, id, author, index int
}

// newestFirst implements heap.Interface with the newest tweet at index 0.
type newestFirst []cursor

func (h newestFirst) Len() int           { return len(h) }
func (h newestFirst) Less(i, j int) bool { return h[i].time > h[j].time }
func (h newestFirst) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }

func (h *newestFirst) Push(entry any) {
	*h = append(*h, entry.(cursor))
}

func (h *newestFirst) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

type Twitter struct {
	clock int
	// tweets holds each user's own tweets, oldest first.
	tweets    map[int][]post
	following map[int]map[int]struct{}
}

func NewTwitter() *Twitter {
	return &Twitter{tweets: make(map[int][]post), following: make(map[int]map[int]struct{})}
}

func (t *Twitter) PostTweet(userId int, tweetId int) {
	t.tweets[userId] = append(t.tweets[userId], post{t.clock, tweetId})
	t.clock++
}

func (t *Twitter) GetNewsFeed(userId int) []int {
	followees := t.following[userId]
	// One cursor per author, at that author's newest tweet.
	cursors := make(newestFirst, 0, len(followees)+1)
	addNewest := func(author int) {
		timeline := t.tweets[author]
		if len(timeline) > 0 {
			last := len(timeline) - 1
			cursors = append(cursors, cursor{timeline[last].time, timeline[last].id, author, last})
		}
	}
	addNewest(userId)
	for followee := range followees {
		addNewest(followee)
	}
	heap.Init(&cursors)
	feed := make([]int, 0, feedSize)
	for cursors.Len() > 0 && len(feed) < feedSize {
		newest := heap.Pop(&cursors).(cursor)
		feed = append(feed, newest.id)
		if newest.index > 0 {
			older := t.tweets[newest.author][newest.index-1]
			heap.Push(&cursors, cursor{older.time, older.id, newest.author, newest.index - 1})
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
