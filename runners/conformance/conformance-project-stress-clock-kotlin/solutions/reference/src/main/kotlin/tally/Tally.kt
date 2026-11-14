package tally

/** The entry class, which worker threads share from level 2. */
class Tally {
    private val counts = Counts()

    suspend fun add(key: String, amount: Int): Int = counts.add(key, amount)

    suspend fun count(key: String): Int = counts.of(key)

    suspend fun take(key: String, amount: Int): Boolean = counts.take(key, amount)
}
