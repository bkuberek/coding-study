// No `Clone`: an account is one real-world entity, and nothing here needs a copy of it.
struct Account {
    balance: i32,
    transfers: i32,
}

impl Account {
    fn debit(&mut self, amount: i32) {
        self.balance -= amount;
        self.transfers += 1;
    }

    fn credit(&mut self, amount: i32) {
        self.balance += amount;
        self.transfers += 1;
    }
}

pub struct Ledger {
    accounts: Vec<Account>,
}

impl Ledger {
    pub fn new(balances: Vec<i32>) -> Self {
        let accounts = balances
            .into_iter()
            .map(|balance| Account {
                balance,
                transfers: 0,
            })
            .collect();
        Ledger { accounts }
    }

    pub fn transfer(&mut self, from_account: i32, to_account: i32, amount: i32) -> bool {
        let (from, to) = (from_account as usize, to_account as usize);
        if from == to || self.accounts[from].balance < amount {
            return false;
        }
        // Two `&mut self.accounts[..]` alive at once do not compile, and a clone of the payee
        // would take the credit instead of the account. Each borrow below ends before the next
        // one starts, so neither is needed.
        self.accounts[from].debit(amount);
        self.accounts[to].credit(amount);
        true
    }

    pub fn balance(&mut self, account: i32) -> i32 {
        self.accounts[account as usize].balance
    }

    pub fn transfers(&mut self, account: i32) -> i32 {
        self.accounts[account as usize].transfers
    }
}
