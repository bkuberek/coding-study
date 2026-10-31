package bank.accounts

/** The balance of every account, by id. */
class Balances {
    private val balances = mutableMapOf<String, Long>()

    fun open(accountId: String): Boolean = balances.putIfAbsent(accountId, 0L) == null

    fun has(accountId: String): Boolean = accountId in balances

    fun of(accountId: String): Long = balances.getValue(accountId)

    fun add(accountId: String, amount: Long): Long = (balances.getValue(accountId) + amount).also { balances[accountId] = it }
}
