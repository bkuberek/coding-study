package bank

import bank.accounts.Balances

/** Accounts that hold a balance, keyed by account id. */
class Bank {
    private val balances = Balances()

    fun createAccount(timestamp: Long, accountId: String): Boolean = balances.open(accountId)

    fun deposit(timestamp: Long, accountId: String, amount: Long): Long =
        if (balances.has(accountId)) balances.add(accountId, amount) else -1

    fun transfer(timestamp: Long, sourceId: String, targetId: String, amount: Long): Long {
        val known = balances.has(sourceId) && balances.has(targetId)
        if (!known || sourceId == targetId || balances.of(sourceId) < amount) {
            return -1
        }
        balances.add(targetId, amount)
        return balances.add(sourceId, -amount)
    }
}
