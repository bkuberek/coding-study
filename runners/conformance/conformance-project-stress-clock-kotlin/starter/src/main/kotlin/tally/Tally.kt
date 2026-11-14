package tally

/** The entry class: `cstudy` loads `tally.Tally`. */
class Tally {
    suspend fun add(key: String, amount: Int): Int = throw NotImplementedError("Not implemented")

    suspend fun count(key: String): Int = throw NotImplementedError("Not implemented")
}
