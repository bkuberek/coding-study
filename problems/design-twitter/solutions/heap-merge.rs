use std::collections::{BinaryHeap, HashMap, HashSet};

const FEED_SIZE: usize = 10;

pub struct Twitter {
    clock: i32,
    /// Each user's own tweets, oldest first, as (post time, tweet id).
    tweets: HashMap<i32, Vec<(i32, i32)>>,
    following: HashMap<i32, HashSet<i32>>,
}

impl Twitter {
    pub fn new() -> Self {
        Twitter {
            clock: 0,
            tweets: HashMap::new(),
            following: HashMap::new(),
        }
    }

    pub fn post_tweet(&mut self, user_id: i32, tweet_id: i32) {
        self.tweets
            .entry(user_id)
            .or_default()
            .push((self.clock, tweet_id));
        self.clock += 1;
    }

    pub fn get_news_feed(&mut self, user_id: i32) -> Vec<i32> {
        let followees = self.following.get(&user_id).into_iter().flatten();
        let authors = followees.copied().chain([user_id]);
        // One entry per author: (post time, tweet id, author, index in their timeline). Times
        // are unique, so the max-heap puts the newest tweet at the root.
        let mut heap: BinaryHeap<(i32, i32, i32, usize)> = authors
            .filter_map(|author| {
                let timeline = self.tweets.get(&author)?;
                let &(time, tweet_id) = timeline.last()?;
                Some((time, tweet_id, author, timeline.len() - 1))
            })
            .collect();
        let mut feed = Vec::with_capacity(FEED_SIZE);
        while feed.len() < FEED_SIZE {
            let Some((_, tweet_id, author, index)) = heap.pop() else {
                break;
            };
            feed.push(tweet_id);
            if index > 0 {
                let (time, older) = self.tweets[&author][index - 1];
                heap.push((time, older, author, index - 1));
            }
        }
        feed
    }

    pub fn follow(&mut self, follower_id: i32, followee_id: i32) {
        if follower_id != followee_id {
            self.following
                .entry(follower_id)
                .or_default()
                .insert(followee_id);
        }
    }

    pub fn unfollow(&mut self, follower_id: i32, followee_id: i32) {
        if let Some(followees) = self.following.get_mut(&follower_id) {
            followees.remove(&followee_id);
        }
    }
}
