//! Jobs that run at a time of their own: earliest due first, then in booking order.
//!
//! The scheduler never sees an account, so it holds any kind of job `J`.

use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};

/// The number of a booking: 1 for the first one, then counting up.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Ticket(pub u64);

/// A place in the run order. The derived `Ord` compares the fields in the order they are
/// declared: the due time, then the ticket, so bookings due at the same time keep their order.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct Slot {
    due: i64,
    ticket: Ticket,
}

/// Booked jobs and the order they run in.
///
/// A cancelled job leaves `pending` at once, but its slot stays in the queue until it reaches
/// the head, where `pop_due` drops it.
pub struct Scheduler<J> {
    queue: BinaryHeap<Reverse<Slot>>,
    pending: HashMap<Ticket, J>,
    booked: u64,
}

// Written by hand: `#[derive(Default)]` would require `J: Default`, which no job needs.
impl<J> Default for Scheduler<J> {
    fn default() -> Self {
        Scheduler {
            queue: BinaryHeap::new(),
            pending: HashMap::new(),
            booked: 0,
        }
    }
}

impl<J> Scheduler<J> {
    /// Books `job` to run at `due` and returns its ticket.
    pub fn book(&mut self, due: i64, job: J) -> Ticket {
        self.booked += 1;
        let ticket = Ticket(self.booked);
        self.queue.push(Reverse(Slot { due, ticket }));
        self.pending.insert(ticket, job);
        ticket
    }

    /// The job booked with `ticket`, while it has neither run nor been cancelled.
    pub fn pending(&self, ticket: Ticket) -> Option<&J> {
        self.pending.get(&ticket)
    }

    /// Cancels a pending job; false when it is not pending.
    pub fn cancel(&mut self, ticket: Ticket) -> bool {
        self.pending.remove(&ticket).is_some()
    }

    /// The next pending job due at or before `now`, with its due time, in run order; it is no
    /// longer pending afterwards.
    pub fn pop_due(&mut self, now: i64) -> Option<(i64, J)> {
        while let Some(&Reverse(slot)) = self.queue.peek() {
            if slot.due > now {
                break;
            }
            self.queue.pop();
            if let Some(job) = self.pending.remove(&slot.ticket) {
                return Some((slot.due, job));
            }
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::{Scheduler, Ticket};

    fn run_until(scheduler: &mut Scheduler<&'static str>, now: i64) -> Vec<(i64, &'static str)> {
        std::iter::from_fn(|| scheduler.pop_due(now)).collect()
    }

    #[test]
    fn tickets_count_bookings_from_one() {
        let mut scheduler = Scheduler::default();
        scheduler.book(50, "a");
        assert_eq!(scheduler.book(40, "b"), Ticket(2));
    }

    #[test]
    fn the_earliest_due_runs_first_whatever_the_booking_order() {
        let mut scheduler = Scheduler::default();
        scheduler.book(30, "late");
        scheduler.book(10, "early");
        assert_eq!(run_until(&mut scheduler, 30), [(10, "early"), (30, "late")]);
    }

    #[test]
    fn jobs_due_together_run_in_booking_order() {
        let mut scheduler = Scheduler::default();
        for job in ["first", "second", "third"] {
            scheduler.book(40, job);
        }
        scheduler.book(33, "sooner");
        assert_eq!(
            run_until(&mut scheduler, 40),
            [(33, "sooner"), (40, "first"), (40, "second"), (40, "third")]
        );
    }

    #[test]
    fn a_job_due_exactly_now_runs() {
        let mut scheduler = Scheduler::default();
        scheduler.book(20, "job");
        assert_eq!(run_until(&mut scheduler, 20), [(20, "job")]);
    }

    #[test]
    fn a_job_due_later_waits() {
        let mut scheduler = Scheduler::default();
        scheduler.book(20, "job");
        assert_eq!(run_until(&mut scheduler, 19), []);
    }

    #[test]
    fn a_cancelled_job_never_runs() {
        let mut scheduler = Scheduler::default();
        let ticket = scheduler.book(20, "cancelled");
        scheduler.book(25, "kept");
        scheduler.cancel(ticket);
        assert_eq!(run_until(&mut scheduler, 30), [(25, "kept")]);
    }

    #[test]
    fn a_job_cancels_once() {
        let mut scheduler = Scheduler::default();
        let ticket = scheduler.book(20, "job");
        scheduler.cancel(ticket);
        assert!(!scheduler.cancel(ticket));
    }

    #[test]
    fn a_job_that_ran_is_no_longer_pending() {
        let mut scheduler = Scheduler::default();
        let ticket = scheduler.book(20, "job");
        run_until(&mut scheduler, 20);
        assert_eq!(scheduler.pending(ticket), None);
    }

    #[test]
    fn an_unknown_ticket_is_not_pending() {
        let scheduler: Scheduler<&str> = Scheduler::default();
        assert_eq!(scheduler.pending(Ticket(1)), None);
    }
}
