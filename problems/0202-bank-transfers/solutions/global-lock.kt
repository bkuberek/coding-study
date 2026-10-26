import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class Bank(balances: LongArray) {
    private val balances = balances.copyOf()
    private val lock = ReentrantLock()

    fun transfer(fromAccount: Int, toAccount: Int, amount: Long): Boolean =
        lock.withLock {
            if (!exists(fromAccount) || !exists(toAccount) || balances[fromAccount] < amount) {
                false
            } else {
                balances[fromAccount] -= amount
                balances[toAccount] += amount
                true
            }
        }

    fun balance(account: Int): Long = lock.withLock { if (exists(account)) balances[account] else -1L }

    fun total(): Long = lock.withLock { balances.sum() }

    private fun exists(account: Int): Boolean = account in balances.indices
}
