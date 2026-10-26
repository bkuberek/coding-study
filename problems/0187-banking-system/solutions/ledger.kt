import java.util.ArrayDeque
import java.util.TreeMap

private const val CASHBACK_DELAY = 86_400_000L
private const val CASHBACK_PERCENT = 2L

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
}

private class Payment(val id: String, val accountId: String, val cashback: Long, val due: Long) {
    var received = false
}

class BankingSystem {
    private val accounts = HashMap<String, Account>()
    private val mergedInto = HashMap<String, String>()
    private val payments = HashMap<String, Payment>()

    /** The delay is constant and timestamps increase, so cashbacks fall due in payment order. */
    private val pending = ArrayDeque<Payment>()

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
        if (source === target || source.balance < amount) {
            return -1
        }
        target.changeBalance(timestamp, amount)
        source.outgoing += amount
        return source.changeBalance(timestamp, -amount)
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
    fun pay(timestamp: Long, accountId: String, amount: Long): String {
        settle(timestamp)
        val account = open(accountId)
        if (account == null || account.balance < amount) {
            return ""
        }
        account.changeBalance(timestamp, -amount)
        account.outgoing += amount
        val payment = Payment(
            id = "payment${payments.size + 1}",
            accountId = accountId,
            cashback = amount * CASHBACK_PERCENT / 100,
            due = timestamp + CASHBACK_DELAY,
        )
        payments[payment.id] = payment
        pending.addLast(payment)
        return payment.id
    }

    fun paymentStatus(timestamp: Long, accountId: String, paymentId: String): String {
        settle(timestamp)
        val payment = payments[paymentId] ?: return ""
        if (open(accountId) == null || owner(payment.accountId) != accountId) {
            return ""
        }
        return if (payment.received) "CASHBACK_RECEIVED" else "IN_PROGRESS"
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

    /** Credit every cashback due at or before [timestamp], at its own due time. */
    private fun settle(timestamp: Long) {
        while (pending.isNotEmpty() && pending.peekFirst().due <= timestamp) {
            val payment = pending.pollFirst()
            accounts.getValue(owner(payment.accountId)).changeBalance(payment.due, payment.cashback)
            payment.received = true
        }
    }
}
