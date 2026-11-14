package bank

/**
 * Every account by id, open or merged away. A merged-away account stays, so `getBalance` can
 * still answer for the times before its merge, but every other lookup treats it as missing.
 */
internal class Ledger {
    private val accounts = HashMap<String, Account>()

    /** Adds an account with balance 0 at time [at]; false when the id is known, open or not. */
    fun open(at: Long, id: String): Boolean {
        if (id in accounts) {
            return false
        }
        accounts[id] = Account(id, openedAt = at)
        return true
    }

    /** The account with this id, open or merged away. */
    fun find(id: String): Account? = accounts[id]

    /** The open account with this id. */
    fun findOpen(id: String): Account? = accounts[id]?.takeIf { it.isOpen }

    /** The open account that holds [id]'s money now, following merges; [id] must be one the ledger has opened. */
    fun holder(id: String): Account = accounts.getValue(id).holder()

    /** Folds [otherId] into [id] at time [at]; false, changing nothing, when the ids are equal or either account is missing. */
    fun merge(at: Long, id: String, otherId: String): Boolean {
        val kept = findOpen(id) ?: return false
        val other = findOpen(otherId) ?: return false
        if (kept === other) {
            return false
        }
        kept.absorb(other, at)
        return true
    }

    /** The open accounts, in no particular order. */
    fun openAccounts(): Sequence<Account> = accounts.values.asSequence().filter { it.isOpen }
}
