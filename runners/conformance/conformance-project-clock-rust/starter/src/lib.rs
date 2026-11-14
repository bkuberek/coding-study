//! The entry class, on the virtual clock.

pub struct Inbox {}

impl Inbox {
    pub fn new() -> Self {
        Inbox {}
    }

    pub fn publish(&self, body: String) -> i32 {
        todo!()
    }

    pub async fn receive(&self, wait_ms: i64) -> String {
        todo!()
    }
}
