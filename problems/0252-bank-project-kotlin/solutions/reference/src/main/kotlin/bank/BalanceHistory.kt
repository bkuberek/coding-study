package bank

import java.util.TreeMap

/**
 * An account's balance after each moment it changed, keyed by time. Several changes at one
 * moment keep only the balance after the last, which is the one every later read sees.
 */
internal class BalanceHistory {
    private val balances = TreeMap<Long, Long>()

    /** Records [balance] as the balance after the changes at time [at]. */
    fun record(at: Long, balance: Long) {
        balances[at] = balance
    }

    /** The balance after every change at or before [time]; null before the first change. */
    fun at(time: Long): Long? = balances.floorEntry(time)?.value
}
