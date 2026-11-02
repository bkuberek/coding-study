package tally

/** The entry class, which worker threads share from level 2. */
class Tally {
    private val counts = Counts()

    fun add(key: String, amount: Int): Int = counts.add(key, amount)

    fun count(key: String): Int = counts.of(key)

    fun take(key: String, amount: Int): Boolean = counts.take(key, amount)
}
