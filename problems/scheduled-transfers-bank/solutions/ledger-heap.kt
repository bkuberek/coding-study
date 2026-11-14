import java.util.PriorityQueue
import java.util.TreeMap

private class Account(val id: String, val createdAt: Long) {
    var balance = 0L
        private set
    var outgoing = 0L
    var closedAt: Long? = null

    /** Time to balance after the last change at that time: the account's balance history. */
    private val history = TreeMap<Long, Long>()

    init {
        changeBalance(createdAt, 0)
    }

    val isOpen: Boolean get() = closedAt == null

    fun changeBalance(timestamp: Long, delta: Long): Long {
        balance += delta
        history[timestamp] = balance
        return balance
    }

    fun balanceAt(moment: Long): Long {
        val closed = closedAt
        if (moment < createdAt || (closed != null && moment >= closed)) {
            return -1
        }
        return history.floorEntry(moment).value
    }

    fun canSend(target: Account, amount: Long): Boolean = this !== target && balance >= amount

    fun send(target: Account, timestamp: Long, amount: Long): Long {
        target.changeBalance(timestamp, amount)
        outgoing += amount
        return changeBalance(timestamp, -amount)
    }
}

private class ScheduledTransfer(
    val number: Int,
    val sourceId: String,
    val targetId: String,
    val amount: Long,
    val due: Long,
) {
    val id = "transfer$number"
    var pending = true
}

class Bank {
    private val accounts = HashMap<String, Account>()
    private val mergedInto = HashMap<String, String>()
    private val transfers = HashMap<String, ScheduledTransfer>()

    /** Earliest due first, ties in scheduling order. A cancelled transfer stays here until it reaches the head. */
    private val due = PriorityQueue(compareBy<ScheduledTransfer>({ it.due }, { it.number }))

    // Level 1
    fun createAccount(timestamp: Long, accountId: String): Boolean {
        settle(timestamp)
        if (accountId in accounts) {
            return false
        }
        accounts[accountId] = Account(accountId, timestamp)
        return true
    }

    fun deposit(timestamp: Long, accountId: String, amount: Long): Long {
        settle(timestamp)
        return open(accountId)?.changeBalance(timestamp, amount) ?: -1
    }

    fun transfer(timestamp: Long, sourceId: String, targetId: String, amount: Long): Long {
        settle(timestamp)
        val source = open(sourceId) ?: return -1
        val target = open(targetId) ?: return -1
        if (!source.canSend(target, amount)) {
            return -1
        }
        return source.send(target, timestamp, amount)
    }

    // Level 2
    fun topSpenders(timestamp: Long, n: Int): List<String> {
        settle(timestamp)
        return accounts.values
            .filter { it.isOpen }
            .sortedWith(compareByDescending<Account> { it.outgoing }.thenBy { it.id })
            .take(n)
            .map { "${it.id}(${it.outgoing})" }
    }

    // Level 3
    fun scheduleTransfer(timestamp: Long, sourceId: String, targetId: String, amount: Long, delay: Long): String {
        settle(timestamp)
        val source = open(sourceId) ?: return ""
        val target = open(targetId) ?: return ""
        if (source === target) {
            return ""
        }
        val scheduled = ScheduledTransfer(
            number = transfers.size + 1,
            sourceId = sourceId,
            targetId = targetId,
            amount = amount,
            due = timestamp + delay,
        )
        transfers[scheduled.id] = scheduled
        due.add(scheduled)
        return scheduled.id
    }

    fun cancelTransfer(timestamp: Long, accountId: String, transferId: String): Boolean {
        settle(timestamp)
        val scheduled = transfers[transferId] ?: return false
        if (open(accountId) == null || !scheduled.pending || owner(scheduled.sourceId) != accountId) {
            return false
        }
        scheduled.pending = false
        return true
    }

    // Level 4
    fun mergeAccounts(timestamp: Long, accountId: String, otherId: String): Boolean {
        settle(timestamp)
        val account = open(accountId) ?: return false
        val other = open(otherId) ?: return false
        if (account === other) {
            return false
        }
        account.changeBalance(timestamp, other.balance)
        account.outgoing += other.outgoing
        other.closedAt = timestamp
        mergedInto[otherId] = accountId
        return true
    }

    fun getBalance(timestamp: Long, accountId: String, timeAt: Long): Long {
        settle(timestamp)
        return accounts[accountId]?.balanceAt(timeAt) ?: -1
    }

    private fun open(accountId: String): Account? = accounts[accountId]?.takeIf { it.isOpen }

    /** The open account that now holds [accountId], following merges. */
    private fun owner(accountId: String): String = generateSequence(accountId) { mergedInto[it] }.last()

    /** Run every scheduled transfer due at or before [timestamp], each at its own due time. */
    private fun settle(timestamp: Long) {
        while (due.isNotEmpty() && due.peek().due <= timestamp) {
            val scheduled = due.poll()
            if (!scheduled.pending) {
                continue
            }
            scheduled.pending = false
            val source = accounts.getValue(owner(scheduled.sourceId))
            val target = accounts.getValue(owner(scheduled.targetId))
            if (source.canSend(target, scheduled.amount)) {
                source.send(target, scheduled.due, scheduled.amount)
            }
        }
    }
}
