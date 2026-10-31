package bank

import bank.schedule.ScheduledTransfer
import bank.schedule.Scheduler

/**
 * Bank accounts that hold whole amounts of money and send money to one another: the class
 * that `cstudy submit` and the tests drive.
 *
 * Every public method first runs the scheduled transfers that fell due by its timestamp, so
 * it sees the bank as it is at that moment. The inner classes report "nothing here" as
 * `null`; only this class turns that into the API's sentinels.
 */
class Bank {
    private val ledger = Ledger()
    private val scheduler = Scheduler()

    /** Opens an account with balance 0; false when the id is taken, also by an account merged away. */
    fun createAccount(timestamp: Long, accountId: String): Boolean {
        settle(timestamp)
        return ledger.open(timestamp, accountId)
    }

    /** Adds [amount] to the account and returns its new balance; -1 when there is no such account. */
    fun deposit(timestamp: Long, accountId: String, amount: Long): Long {
        settle(timestamp)
        val account = ledger.findOpen(accountId) ?: return FAILED
        return account.deposit(timestamp, amount)
    }

    /**
     * Moves [amount] from the source account to the target account and returns the source's
     * new balance; -1, changing nothing, when it cannot.
     */
    fun transfer(timestamp: Long, sourceId: String, targetId: String, amount: Long): Long {
        settle(timestamp)
        val source = ledger.findOpen(sourceId) ?: return FAILED
        val target = ledger.findOpen(targetId) ?: return FAILED
        if (!source.canSend(target, amount)) {
            return FAILED
        }
        return source.send(target, timestamp, amount)
    }

    /** The first [n] accounts by money sent, as `"<id>(<total>)"`. */
    fun topSpenders(timestamp: Long, n: Int): List<String> {
        settle(timestamp)
        return ledger.openAccounts()
            .sortedWith(BY_SPENDING)
            .take(n)
            .map { "${it.id}(${it.sent})" }
            .toList()
    }

    /**
     * Books [amount] to move from the source to the target at `timestamp + delay` and returns
     * the booking's id; "" when either account is missing or both are the same.
     */
    fun scheduleTransfer(timestamp: Long, sourceId: String, targetId: String, amount: Long, delay: Long): String {
        settle(timestamp)
        val source = ledger.findOpen(sourceId) ?: return NOT_BOOKED
        val target = ledger.findOpen(targetId) ?: return NOT_BOOKED
        if (source === target) {
            return NOT_BOOKED
        }
        return scheduler.book(ScheduledTransfer(sourceId, targetId, amount, due = timestamp + delay))
    }

    /** Cancels a booked transfer that has not run yet; only the account that sends it may. */
    fun cancelTransfer(timestamp: Long, accountId: String, transferId: String): Boolean {
        settle(timestamp)
        val transfer = scheduler.pending(transferId) ?: return false
        return ledger.holder(transfer.sourceId).id == accountId && scheduler.cancel(transferId)
    }

    /** Folds [otherId] into [accountId]; false, changing nothing, when the ids are equal or either account is missing. */
    fun mergeAccounts(timestamp: Long, accountId: String, otherId: String): Boolean {
        settle(timestamp)
        return ledger.merge(timestamp, accountId, otherId)
    }

    /** The balance the account had at [timeAt]; -1 when it did not exist then. */
    fun getBalance(timestamp: Long, accountId: String, timeAt: Long): Long {
        settle(timestamp)
        return ledger.find(accountId)?.balanceAt(timeAt) ?: FAILED
    }

    /**
     * Runs every scheduled transfer due by [now], each at its own due time. A transfer the
     * source cannot pay then, or one between two accounts merged into one, is skipped.
     */
    private fun settle(now: Long) {
        for (transfer in scheduler.takeDue(now)) {
            val source = ledger.holder(transfer.sourceId)
            val target = ledger.holder(transfer.targetId)
            if (source.canSend(target, transfer.amount)) {
                source.send(target, transfer.due, transfer.amount)
            }
        }
    }

    private companion object {
        const val FAILED = -1L
        const val NOT_BOOKED = ""

        /** Larger totals sent first, equal totals by id. */
        val BY_SPENDING = compareByDescending<Account> { it.sent }.thenBy { it.id }
    }
}
