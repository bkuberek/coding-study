// Debug: Clone Mutation. Some tests fail: find the bug and fix it.
#[derive(Clone)]
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
        let mut payee = self.accounts[to].clone();
        let payer = &mut self.accounts[from];
        payer.debit(amount);
        payee.credit(amount);
        true
    }

    pub fn balance(&mut self, account: i32) -> i32 {
        self.accounts[account as usize].balance
    }

    pub fn transfers(&mut self, account: i32) -> i32 {
        self.accounts[account as usize].transfers
    }
}
