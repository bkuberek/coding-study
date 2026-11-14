use std::collections::{HashMap, HashSet, VecDeque};

struct FinePolicy {
    per_day: i64,
}

impl FinePolicy {
    fn fine(&self, due: i64, returned: i64) -> i64 {
        (returned - due).max(0) * self.per_day
    }
}

/// All copies of one ISBN, with the members waiting for one.
#[derive(Default)]
struct Title {
    copies: i32,
    on_loan: i32,
    /// Members with a copy set aside for them.
    reserved: HashSet<String>,
    waiting: VecDeque<String>,
}

impl Title {
    fn free(&self) -> i32 {
        self.copies - self.on_loan - self.reserved.len() as i32
    }

    /// Keeps the invariant that a free copy never sits on the shelf while someone is waiting.
    fn assign_free_copies(&mut self) {
        while self.free() > 0 {
            let Some(next) = self.waiting.pop_front() else {
                break;
            };
            self.reserved.insert(next);
        }
    }
}

struct Member {
    max_loans: usize,
    /// ISBN to due day.
    loans: HashMap<String, i64>,
    fines: i64,
}

impl Member {
    fn can_borrow(&self, isbn: &str) -> bool {
        self.fines == 0 && !self.loans.contains_key(isbn) && self.loans.len() < self.max_loans
    }
}

pub struct Library {
    loan_days: i64,
    fine_policy: FinePolicy,
    titles: HashMap<String, Title>,
    members: HashMap<String, Member>,
}

impl Library {
    pub fn new(loan_days: i32, fine_per_day: i32) -> Self {
        Library {
            loan_days: i64::from(loan_days),
            fine_policy: FinePolicy {
                per_day: i64::from(fine_per_day),
            },
            titles: HashMap::new(),
            members: HashMap::new(),
        }
    }

    pub fn add_book(&mut self, isbn: String, copies: i32) -> i32 {
        let title = self.titles.entry(isbn).or_default();
        title.copies += copies;
        title.assign_free_copies();
        title.copies
    }

    pub fn add_member(&mut self, member_id: String, max_loans: i32) -> bool {
        if self.members.contains_key(&member_id) {
            return false;
        }
        self.members.insert(
            member_id,
            Member {
                max_loans: usize::try_from(max_loans).unwrap_or(0),
                loans: HashMap::new(),
                fines: 0,
            },
        );
        true
    }

    pub fn checkout(&mut self, day: i64, member_id: String, isbn: String) -> i64 {
        let (Some(member), Some(title)) =
            (self.members.get_mut(&member_id), self.titles.get_mut(&isbn))
        else {
            return -1;
        };
        if !member.can_borrow(&isbn) {
            return -1;
        }
        if !title.reserved.remove(&member_id) && title.free() == 0 {
            return -1;
        }
        title.on_loan += 1;
        let due = day + self.loan_days;
        member.loans.insert(isbn, due);
        due
    }

    pub fn return_book(&mut self, day: i64, member_id: String, isbn: String) -> i64 {
        let Some(member) = self.members.get_mut(&member_id) else {
            return -1;
        };
        let Some(due) = member.loans.remove(&isbn) else {
            return -1;
        };
        let fine = self.fine_policy.fine(due, day);
        member.fines += fine;
        if let Some(title) = self.titles.get_mut(&isbn) {
            title.on_loan -= 1;
            title.assign_free_copies();
        }
        fine
    }

    pub fn place_hold(&mut self, day: i64, member_id: String, isbn: String) -> i32 {
        let (Some(member), Some(title)) =
            (self.members.get(&member_id), self.titles.get_mut(&isbn))
        else {
            return -1;
        };
        if title.free() > 0 {
            return -1;
        }
        let queued = title.waiting.contains(&member_id);
        if member.loans.contains_key(&isbn) || title.reserved.contains(&member_id) || queued {
            return -1;
        }
        title.waiting.push_back(member_id);
        title.waiting.len() as i32
    }

    pub fn cancel_hold(&mut self, day: i64, member_id: String, isbn: String) -> bool {
        let Some(title) = self.titles.get_mut(&isbn) else {
            return false;
        };
        if let Some(position) = title
            .waiting
            .iter()
            .position(|waiting| *waiting == member_id)
        {
            title.waiting.remove(position);
            return true;
        }
        if title.reserved.remove(&member_id) {
            title.assign_free_copies();
            return true;
        }
        false
    }

    pub fn renew(&mut self, day: i64, member_id: String, isbn: String) -> i64 {
        let Some(member) = self.members.get_mut(&member_id) else {
            return -1;
        };
        let Some(due) = member.loans.get_mut(&isbn) else {
            return -1;
        };
        let has_waiting = self
            .titles
            .get(&isbn)
            .is_some_and(|title| !title.waiting.is_empty());
        if day > *due || has_waiting {
            return -1;
        }
        *due += self.loan_days;
        *due
    }

    pub fn fines(&mut self, day: i64, member_id: String) -> i64 {
        self.members
            .get(&member_id)
            .map_or(-1, |member| member.fines)
    }

    pub fn pay_fine(&mut self, day: i64, member_id: String, amount: i64) -> i64 {
        match self.members.get_mut(&member_id) {
            Some(member) => {
                member.fines = (member.fines - amount).max(0);
                member.fines
            }
            None => -1,
        }
    }

    pub fn available(&mut self, day: i64, isbn: String) -> i32 {
        self.titles.get(&isbn).map_or(-1, Title::free)
    }
}
