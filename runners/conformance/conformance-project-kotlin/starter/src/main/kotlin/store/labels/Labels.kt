package store.labels

/** Labels for stock counts, in a package of their own. */
object Labels {
    const val SEPARATOR = ": "

    fun labelFor(name: String, count: Int): String = "$name$SEPARATOR$count"
}
