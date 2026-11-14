package store

import store.labels.Labels

/**
 * The entry class: `cstudy` loads `store.Inventory`. It uses a class of its own package that the
 * reference adds and an object of a subpackage that the starter holds.
 */
class Inventory {
    private val counts = Counts()

    fun add(name: String, count: Int): Int = counts.add(name, count)

    fun label(name: String): String = Labels.labelFor(name, counts.of(name))
}
