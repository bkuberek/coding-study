package bank

/**
 * One bank account, opened at time [openedAt]: its balance, the money it has sent, its
 * balance history and, once another account absorbs it, where it went.
 */
internal class Account(val id: String, openedAt: Long) {
    var balance = 0L
        private set

    /** The total of every successful transfer out of this account, merged accounts' included. */
    var sent = 0L
        private set

    private val history = BalanceHistory().apply { record(openedAt, 0L) }

    /** The merge that absorbed this account; null while it is open. */
    private var merge: Merge? = null

    val isOpen: Boolean
        get() = merge == null

    /** The open account that holds this one's money now: itself, or the end of its chain of merges. */
    fun holder(): Account = generateSequence(this) { it.merge?.into }.last()

    /** Adds [amount] at time [at] and returns the new balance. */
    fun deposit(at: Long, amount: Long): Long {
        changeBalance(at, amount)
        return balance
    }

    /** Whether this account may send [amount] to [to]: never to itself, and only from a balance that covers it. */
    fun canSend(to: Account, amount: Long): Boolean = to !== this && balance >= amount

    /** Moves [amount] to [to] at time [at], counts it as sent, and returns the new balance. The caller checks [canSend] first. */
    fun send(to: Account, at: Long, amount: Long): Long {
        changeBalance(at, -amount)
        to.changeBalance(at, amount)
        sent += amount
        return balance
    }

    /** Folds [other] into this account at time [at]: its balance and its total sent become this one's, and [other] closes. */
    fun absorb(other: Account, at: Long) {
        changeBalance(at, other.balance)
        sent += other.sent
        other.merge = Merge(into = this, at = at)
    }

    /** The balance after every change at or before [time]; null before the account opened and from its merge on. */
    fun balanceAt(time: Long): Long? {
        val mergedAt = merge?.at
        if (mergedAt != null && time >= mergedAt) {
            return null
        }
        return history.at(time)
    }

    private fun changeBalance(at: Long, delta: Long) {
        balance += delta
        history.record(at, balance)
    }

    private class Merge(val into: Account, val at: Long)
}
