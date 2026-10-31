package warmup

/**
 * The warm-up project's code: `cstudy doctor --fix` builds this folder online once, so every
 * library a Kotlin project problem builds with is cached for its offline builds.
 */
class Counter {
    private var count = 0

    fun add(amount: Int): Int {
        count += amount
        return count
    }
}
