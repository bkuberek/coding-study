package bank

/**
 * Bank accounts that hold whole amounts of money and send money to one another: the class
 * that `cstudy submit` and the tests drive.
 */
class Bank {
    private val accounts = mutableMapOf<String, Account>()

    /** Opens an account with balance 0; false when the id is taken. */
    fun createAccount(timestamp: Long, accountId: String): Boolean = TODO("Not implemented")

    /** Adds [amount] to the account and returns its new balance; -1 when there is no such account. */
    fun deposit(timestamp: Long, accountId: String, amount: Long): Long = TODO("Not implemented")

    /**
     * Moves [amount] from the source account to the target account and returns the source's
     * new balance; -1, changing nothing, when it cannot.
     */
    fun transfer(timestamp: Long, sourceId: String, targetId: String, amount: Long): Long = TODO("Not implemented")
}
