class Bank(balances: LongArray) {
    private val balances = balances.copyOf()
    private val locks = Array(balances.size) { Any() }

    fun transfer(fromAccount: Int, toAccount: Int, amount: Long): Boolean {
        if (!exists(fromAccount) || !exists(toAccount)) return false
        synchronized(locks[fromAccount]) {
            synchronized(locks[toAccount]) {
                if (balances[fromAccount] < amount) return false
                balances[fromAccount] -= amount
                balances[toAccount] += amount
                return true
            }
        }
    }

    fun balance(account: Int): Long =
        if (exists(account)) synchronized(locks[account]) { balances[account] } else -1L

    fun total(): Long = sumFrom(0)

    private fun sumFrom(account: Int): Long =
        if (account == balances.size) {
            balances.sum()
        } else {
            synchronized(locks[account]) { sumFrom(account + 1) }
        }

    private fun exists(account: Int): Boolean = account in balances.indices
}
