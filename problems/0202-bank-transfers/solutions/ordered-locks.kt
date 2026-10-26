import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class Bank(balances: LongArray) {
    private val balances = balances.copyOf()
    private val locks = Array(balances.size) { ReentrantLock() }

    fun transfer(fromAccount: Int, toAccount: Int, amount: Long): Boolean {
        if (!exists(fromAccount) || !exists(toAccount)) return false
        val first = locks[minOf(fromAccount, toAccount)]
        val second = locks[maxOf(fromAccount, toAccount)]
        return first.withLock {
            second.withLock {
                if (balances[fromAccount] < amount) {
                    false
                } else {
                    balances[fromAccount] -= amount
                    balances[toAccount] += amount
                    true
                }
            }
        }
    }

    fun balance(account: Int): Long =
        if (exists(account)) locks[account].withLock { balances[account] } else -1L

    fun total(): Long {
        locks.forEach { it.lock() }
        try {
            return balances.sum()
        } finally {
            locks.reversed().forEach { it.unlock() }
        }
    }

    private fun exists(account: Int): Boolean = account in balances.indices
}
