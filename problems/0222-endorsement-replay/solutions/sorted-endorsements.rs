use chrono::NaiveDate;
use rust_decimal::{Decimal, RoundingStrategy};

const CENTS: u32 = 2;

pub struct EndorsedPolicy {
    term_start: NaiveDate,
    term_end: NaiveDate,
    term_days: i64,
    /// Parallel vectors, strictly ascending by effective date: `premiums[i]` is the full-term
    /// premium in force from `dates[i]` until the next date. There is no sorted map in `std`
    /// that iterates by position with a look-ahead, and a `BTreeMap` has no neighbour access.
    dates: Vec<NaiveDate>,
    premiums: Vec<Decimal>,
}

impl EndorsedPolicy {
    pub fn new(term_start: NaiveDate, term_end: NaiveDate, full_term_premium: Decimal) -> Self {
        EndorsedPolicy {
            term_start,
            term_end,
            term_days: (term_end - term_start).num_days(),
            dates: vec![term_start],
            premiums: vec![full_term_premium],
        }
    }

    pub fn endorse(&mut self, effective_date: NaiveDate, full_term_premium: Decimal) -> bool {
        if !self.in_term(effective_date) {
            return false;
        }
        match self.dates.binary_search(&effective_date) {
            // Same date: the later endorsement corrects it.
            Ok(slot) => self.premiums[slot] = full_term_premium,
            Err(slot) => {
                self.dates.insert(slot, effective_date);
                self.premiums.insert(slot, full_term_premium);
            }
        }
        true
    }

    pub fn premium_on(&mut self, on_date: NaiveDate) -> Decimal {
        if !self.in_term(on_date) {
            return Decimal::NEGATIVE_ONE;
        }
        // The entry in force is the last one on or before the day; the first date is `term_start`,
        // so at least one date qualifies.
        let slot = self.dates.partition_point(|date| *date <= on_date) - 1;
        self.premiums[slot]
    }

    pub fn written_premium(&mut self) -> Decimal {
        self.earned_premium(self.term_end)
    }

    pub fn earned_premium(&mut self, as_of_date: NaiveDate) -> Decimal {
        let cutoff = as_of_date.clamp(self.term_start, self.term_end);
        let mut weighted = Decimal::ZERO; // sum of premium * days over the segments before the cutoff, exact
        for (i, &start) in self.dates.iter().enumerate() {
            if start >= cutoff {
                break;
            }
            let end = self.dates.get(i + 1).copied().unwrap_or(self.term_end);
            let days = (end.min(cutoff) - start).num_days();
            weighted += self.premiums[i] * Decimal::from(days);
        }
        // `/` keeps 28 significant digits, so the rounding that follows is exact: a quotient by a
        // count of days never ends in a run of 9s. `MidpointAwayFromZero` is Java's `HALF_UP`.
        (weighted / Decimal::from(self.term_days))
            .round_dp_with_strategy(CENTS, RoundingStrategy::MidpointAwayFromZero)
    }

    /// Whether the day lies in `[term_start, term_end)`.
    fn in_term(&self, day: NaiveDate) -> bool {
        day >= self.term_start && day < self.term_end
    }
}
