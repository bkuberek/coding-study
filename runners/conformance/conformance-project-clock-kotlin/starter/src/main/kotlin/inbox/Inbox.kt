package inbox

/** The entry class: `cstudy` loads `inbox.Inbox` and grades it on the virtual clock. */
class Inbox {
    fun publish(body: String): Int = throw NotImplementedError("Not implemented")

    suspend fun receive(waitMs: Long): String = throw NotImplementedError("Not implemented")

    suspend fun sleep(ms: Long): Long = throw NotImplementedError("Not implemented")

    suspend fun steps(count: Int, ms: Long): List<Long> = throw NotImplementedError("Not implemented")

    suspend fun race(names: String): String = throw NotImplementedError("Not implemented")

    suspend fun hold(): String = throw NotImplementedError("Not implemented")

    suspend fun fail(): String = throw NotImplementedError("Not implemented")

    fun jam(): String = throw NotImplementedError("Not implemented")

    suspend fun leave(): Unit = throw NotImplementedError("Not implemented")
}
