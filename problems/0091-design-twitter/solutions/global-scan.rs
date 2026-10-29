use std::collections::{HashMap, HashSet};

const FEED_SIZE: usize = 10;

pub struct Twitter {
    /// Every tweet ever posted, oldest first, as (author, tweet id).
    timeline: Vec<(i32, i32)>,
    following: HashMap<i32, HashSet<i32>>,
}

impl Twitter {
    pub fn new() -> Self {
        Twitter {
            timeline: Vec::new(),
            following: HashMap::new(),
        }
    }

    pub fn post_tweet(&mut self, user_id: i32, tweet_id: i32) {
        self.timeline.push((user_id, tweet_id));
    }

    pub fn get_news_feed(&mut self, user_id: i32) -> Vec<i32> {
        let followees = self.following.get(&user_id);
        self.timeline
            .iter()
            .rev()
            .filter(|&&(author, _)| {
                author == user_id || followees.is_some_and(|set| set.contains(&author))
            })
            .take(FEED_SIZE)
            .map(|&(_, tweet_id)| tweet_id)
            .collect()
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
