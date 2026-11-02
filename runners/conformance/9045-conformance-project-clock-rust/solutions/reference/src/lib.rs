//! The entry class: `cstudy` uses `inbox::Inbox` and grades it on the virtual clock.
//!
//! `receive`, `sleep`, `steps` and `race` wait on tokio's clock, which the grader pauses. `hold`,
//! `fail`, `jam` and `leave` exist for the runner's conformance: `hold` waits on a notification
//! nobody sends (a deadlock), `fail` panics after a sleep, `jam` parks the case's thread for good
//! (a wait the clock cannot see), and `leave` spawns a task that never ends.

use std::collections::VecDeque;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use tokio::sync::Notify;
use tokio::time::Instant;

const RACE_DELAY: Duration = Duration::from_millis(10);

pub struct Inbox {
    messages: Mutex<VecDeque<String>>,
    arrived: Notify,
    published: Mutex<i32>,
    never: Arc<Notify>,
}

impl Default for Inbox {
    fn default() -> Self {
        Self::new()
    }
}

impl Inbox {
    pub fn new() -> Self {
        Inbox {
            messages: Mutex::new(VecDeque::new()),
            arrived: Notify::new(),
            published: Mutex::new(0),
            never: Arc::new(Notify::new()),
        }
    }

    /// Hands `body` to a waiting or later `receive`; returns how many messages were published.
    pub fn publish(&self, body: String) -> i32 {
        self.messages.lock().unwrap().push_back(body);
        self.arrived.notify_one();
        let mut published = self.published.lock().unwrap();
        *published += 1;
        *published
    }

    /// The next message, or "" once `wait_ms` milliseconds passed without one.
    pub async fn receive(&self, wait_ms: i64) -> String {
        let next = async {
            loop {
                let arrived = self.arrived.notified();
                let message = self.messages.lock().unwrap().pop_front();
                if let Some(body) = message {
                    return body;
                }
                arrived.await;
            }
        };
        let wait = Duration::from_millis(wait_ms as u64);
        tokio::time::timeout(wait, next).await.unwrap_or_default()
    }

    /// Sleeps `ms` milliseconds; returns how long it slept, as tokio's clock measures it.
    pub async fn sleep(&self, ms: i64) -> i64 {
        let start = Instant::now();
        tokio::time::sleep(Duration::from_millis(ms as u64)).await;
        start.elapsed().as_millis() as i64
    }

    /// `count` sleeps of `ms` milliseconds one after another; the time each one ended.
    pub async fn steps(&self, count: i32, ms: i64) -> Vec<i64> {
        let start = Instant::now();
        let mut ended = Vec::new();
        for _ in 0..count {
            tokio::time::sleep(Duration::from_millis(ms as u64)).await;
            ended.push(start.elapsed().as_millis() as i64);
        }
        ended
    }

    /// One task per name, all waking at the same instant; the names in the order they woke,
    /// which is the order tokio spawned them.
    pub async fn race(&self, names: String) -> String {
        let woke = Arc::new(Mutex::new(String::new()));
        let tasks: Vec<_> = names
            .chars()
            .map(|name| {
                let woke = Arc::clone(&woke);
                tokio::spawn(async move {
                    tokio::time::sleep(RACE_DELAY).await;
                    woke.lock().unwrap().push(name);
                })
            })
            .collect();
        for task in tasks {
            task.await.unwrap();
        }
        let woke = woke.lock().unwrap().clone();
        woke
    }

    /// Waits on a notification nobody sends.
    pub async fn hold(&self) -> String {
        self.never.notified().await;
        String::new()
    }

    /// Panics once a short sleep has passed.
    pub async fn fail(&self) -> String {
        tokio::time::sleep(RACE_DELAY / 2).await;
        panic!("conformance failure");
    }

    /// Parks the calling thread for good: a wait the clock cannot see.
    pub fn jam(&self) -> String {
        loop {
            std::thread::park();
        }
    }

    /// Spawns a task that waits for good, and returns.
    pub async fn leave(&self) {
        let never = Arc::clone(&self.never);
        tokio::spawn(async move { never.notified().await });
    }
}
