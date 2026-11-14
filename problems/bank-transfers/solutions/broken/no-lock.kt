class Bank(balances: LongArray) {
    private val balances = balances.copyOf()

    fun transfer(fromAccount: Int, toAccount: Int, amount: Long): Boolean {
        if (!exists(fromAccount) || !exists(toAccount) || balances[fromAccount] < amount) {
            return false
        }
        balances[fromAccount] -= amount
        balances[toAccount] += amount
        return true
    }

    fun balance(account: Int): Long = if (exists(account)) balances[account] else -1L

    fun total(): Long = balances.sum()

    private fun exists(account: Int): Boolean = account in balances.indices
}
