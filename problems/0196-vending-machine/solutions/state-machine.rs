use std::collections::HashMap;

/// A coin count no combination reaches; small enough to add to without overflowing.
const IMPOSSIBLE: i32 = i32::MAX / 2;

#[derive(Clone, Copy, PartialEq, Eq)]
enum State {
    Maintenance,
    Idle,
    HasCredit,
}

impl State {
    fn name(self) -> &'static str {
        match self {
            State::Maintenance => "MAINTENANCE",
            State::Idle => "IDLE",
            State::HasCredit => "HAS_CREDIT",
        }
    }
}

/// The coins inside the machine, by denomination; pays out exact change with the fewest coins.
struct CoinBox {
    /// Largest first.
    denominations: Vec<i32>,
    counts: HashMap<i32, i32>,
}

impl CoinBox {
    fn new(denominations: &[i32]) -> Self {
        let mut sorted = denominations.to_vec();
        sorted.sort_unstable_by(|a, b| b.cmp(a));
        let counts = sorted.iter().map(|&coin| (coin, 0)).collect();
        CoinBox {
            denominations: sorted,
            counts,
        }
    }

    fn accepts(&self, coin: i32) -> bool {
        self.counts.contains_key(&coin)
    }

    fn add(&mut self, coin: i32, count: i32) {
        *self.counts.entry(coin).or_insert(0) += count;
    }

    /// Removes and returns coins worth `amount`, or `None` (changing nothing) when impossible.
    fn pay_out(&mut self, amount: i32) -> Option<Vec<i32>> {
        let coins = self.plan(amount)?;
        for coin in &coins {
            self.add(*coin, -1);
        }
        Some(coins)
    }

    /// The fewest coins; among those, as many of the largest coin as possible, then the next.
    fn plan(&self, amount: i32) -> Option<Vec<i32>> {
        let stock: Vec<(i32, i32)> = self
            .denominations
            .iter()
            .map(|&coin| (coin, self.counts[&coin]))
            .collect();
        // fewest[i][a]: the fewest coins making `a` from denominations `i` and smaller.
        let mut fewest = vec![vec![IMPOSSIBLE; amount as usize + 1]; stock.len() + 1];
        fewest[stock.len()][0] = 0;
        for (i, &(coin, available)) in stock.iter().enumerate().rev() {
            for a in 0..=amount {
                for k in 0..=available.min(a / coin) {
                    let candidate = k + fewest[i + 1][(a - k * coin) as usize];
                    let cell = &mut fewest[i][a as usize];
                    *cell = (*cell).min(candidate);
                }
            }
        }
        if fewest[0][amount as usize] == IMPOSSIBLE {
            return None;
        }
        let mut coins = Vec::new();
        let mut remaining = amount;
        for (i, &(coin, available)) in stock.iter().enumerate() {
            for k in (0..=available.min(remaining / coin)).rev() {
                if k + fewest[i + 1][(remaining - k * coin) as usize]
                    == fewest[i][remaining as usize]
                {
                    coins.resize(coins.len() + k as usize, coin);
                    remaining -= k * coin;
                    break;
                }
            }
        }
        Some(coins)
    }
}

struct Slot {
    price: i32,
    count: i32,
}

pub struct VendingMachine {
    state: State,
    coins: CoinBox,
    slots: HashMap<String, Slot>,
    credit: i32,
    tray: Vec<i32>,
}

impl VendingMachine {
    pub fn new(denominations: Vec<i32>) -> Self {
        VendingMachine {
            state: State::Maintenance,
            coins: CoinBox::new(&denominations),
            slots: HashMap::new(),
            credit: 0,
            tray: Vec::new(),
        }
    }

    pub fn service(&mut self, enabled: bool) -> bool {
        match (enabled, self.state) {
            (true, State::Idle) => self.state = State::Maintenance,
            (false, State::Maintenance) => self.state = State::Idle,
            _ => return false,
        }
        true
    }

    pub fn stock(&mut self, slot: String, price: i32, count: i32) -> bool {
        if self.state != State::Maintenance {
            return false;
        }
        let item = self.slots.entry(slot).or_insert(Slot { price, count: 0 });
        item.price = price;
        item.count += count;
        true
    }

    pub fn load_coins(&mut self, coin: i32, count: i32) -> bool {
        if self.state != State::Maintenance || !self.coins.accepts(coin) {
            return false;
        }
        self.coins.add(coin, count);
        true
    }

    pub fn insert(&mut self, coin: i32) -> i32 {
        if self.state == State::Maintenance || !self.coins.accepts(coin) {
            self.tray.push(coin);
            return -1;
        }
        self.coins.add(coin, 1);
        self.credit += coin;
        self.state = State::HasCredit;
        self.credit
    }

    pub fn select(&mut self, slot: String) -> String {
        if self.state == State::Maintenance {
            return "OUT_OF_SERVICE".to_string();
        }
        let Some(item) = self.slots.get_mut(&slot) else {
            return "UNKNOWN_SLOT".to_string();
        };
        if item.count == 0 {
            return "SOLD_OUT".to_string();
        }
        if self.credit < item.price {
            return "INSUFFICIENT_CREDIT".to_string();
        }
        let Some(change) = self.coins.pay_out(self.credit - item.price) else {
            return "NO_CHANGE".to_string();
        };
        item.count -= 1;
        self.finish(change);
        "DISPENSED".to_string()
    }

    pub fn refund(&mut self) -> i32 {
        if self.state != State::HasCredit {
            return 0;
        }
        let amount = self.credit;
        let change = self.coins.pay_out(amount).unwrap_or_default();
        self.finish(change);
        amount
    }

    pub fn collect(&mut self) -> Vec<i32> {
        let mut coins = std::mem::take(&mut self.tray);
        coins.sort_unstable_by(|a, b| b.cmp(a));
        coins
    }

    pub fn state(&mut self) -> String {
        self.state.name().to_string()
    }

    pub fn stock_of(&mut self, slot: String) -> i32 {
        self.slots.get(&slot).map_or(-1, |item| item.count)
    }

    /// Returns change to the tray and ends the transaction.
    fn finish(&mut self, change: Vec<i32>) {
        self.tray.extend(change);
        self.credit = 0;
        self.state = State::Idle;
    }
}
