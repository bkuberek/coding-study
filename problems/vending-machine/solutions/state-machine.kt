import java.util.TreeMap

private enum class State { MAINTENANCE, IDLE, HAS_CREDIT }

private const val IMPOSSIBLE = Int.MAX_VALUE / 2

/** The coins inside the machine, by denomination; pays out exact change with the fewest coins. */
private class CoinBox(denominations: IntArray) {
    private val counts = TreeMap<Int, Int>(reverseOrder()).apply { denominations.forEach { put(it, 0) } }

    fun accepts(coin: Int): Boolean = coin in counts

    fun add(coin: Int, count: Int = 1) {
        counts.merge(coin, count, Int::plus)
    }

    /** Remove and return coins worth [amount], or null (changing nothing) when impossible. */
    fun payOut(amount: Int): List<Int>? = plan(amount)?.onEach { add(it, -1) }

    /** Fewest coins; among those, as many of the largest coin as possible, then the next. */
    private fun plan(amount: Int): List<Int>? {
        val stock = counts.entries.map { it.key to it.value }
        // fewest[i][a]: fewest coins making a from denominations i and smaller.
        val fewest = Array(stock.size + 1) { IntArray(amount + 1) { IMPOSSIBLE } }
        fewest[stock.size][0] = 0
        for (i in stock.indices.reversed()) {
            val (coin, available) = stock[i]
            for (a in 0..amount) {
                fewest[i][a] = (0..minOf(available, a / coin)).minOf { k -> k + fewest[i + 1][a - k * coin] }
            }
        }
        if (fewest[0][amount] >= IMPOSSIBLE) {
            return null
        }
        val coins = mutableListOf<Int>()
        var remaining = amount
        stock.forEachIndexed { i, (coin, available) ->
            val used = (minOf(available, remaining / coin) downTo 0)
                .first { k -> k + fewest[i + 1][remaining - k * coin] == fewest[i][remaining] }
            repeat(used) { coins += coin }
            remaining -= used * coin
        }
        return coins
    }
}

private class Slot(var price: Int, var count: Int)

class VendingMachine(denominations: IntArray) {
    private var current = State.MAINTENANCE
    private val coins = CoinBox(denominations)
    private val slots = HashMap<String, Slot>()
    private var credit = 0
    private val tray = mutableListOf<Int>()

    fun service(enabled: Boolean): Boolean {
        current = when {
            enabled && current == State.IDLE -> State.MAINTENANCE
            !enabled && current == State.MAINTENANCE -> State.IDLE
            else -> return false
        }
        return true
    }

    fun stock(slot: String, price: Int, count: Int): Boolean {
        if (current != State.MAINTENANCE) {
            return false
        }
        val item = slots.getOrPut(slot) { Slot(price, 0) }
        item.price = price
        item.count += count
        return true
    }

    fun loadCoins(coin: Int, count: Int): Boolean {
        if (current != State.MAINTENANCE || !coins.accepts(coin)) {
            return false
        }
        coins.add(coin, count)
        return true
    }

    fun insert(coin: Int): Int {
        if (current == State.MAINTENANCE || !coins.accepts(coin)) {
            tray += coin
            return -1
        }
        coins.add(coin)
        credit += coin
        current = State.HAS_CREDIT
        return credit
    }

    fun select(slot: String): String {
        if (current == State.MAINTENANCE) {
            return "OUT_OF_SERVICE"
        }
        val item = slots[slot] ?: return "UNKNOWN_SLOT"
        if (item.count == 0) {
            return "SOLD_OUT"
        }
        if (credit < item.price) {
            return "INSUFFICIENT_CREDIT"
        }
        val change = coins.payOut(credit - item.price) ?: return "NO_CHANGE"
        item.count--
        finish(change)
        return "DISPENSED"
    }

    fun refund(): Int {
        if (current != State.HAS_CREDIT) {
            return 0
        }
        val amount = credit
        finish(coins.payOut(amount).orEmpty())
        return amount
    }

    fun collect(): List<Int> = tray.sortedDescending().also { tray.clear() }

    fun state(): String = current.name

    fun stockOf(slot: String): Int = slots[slot]?.count ?: -1

    /** Return change to the tray and end the transaction. */
    private fun finish(change: List<Int>) {
        tray += change
        credit = 0
        current = State.IDLE
    }
}
