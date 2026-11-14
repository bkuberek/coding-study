// Open addressing with linear probing: a key that finds its home slot taken tries the next one.
//
// Keys are small integers hashed as `key % 8`, so that the collisions are easy to follow.

const val SLOTS = 8
const val DELETED = "<deleted>" // a tombstone: free to reuse, but a search goes on past it

class ProbingSet {
    val slots = arrayOfNulls<Any>(SLOTS) // null is an empty slot

    /** The slots to try for [key]: its home slot, then the next ones, wrapping around. */
    private fun probe(key: Int): List<Int> = List(SLOTS) { step -> (key % SLOTS + step) % SLOTS }

    fun add(key: Int): List<Int> {
        val tried = mutableListOf<Int>()
        var reusable: Int? = null
        for (slot in probe(key)) {
            tried.add(slot)
            if (slots[slot] == key) return tried
            if (slots[slot] == DELETED && reusable == null) reusable = slot
            if (slots[slot] == null) {
                slots[reusable ?: slot] = key
                return tried
            }
        }
        error("full: a real table resizes long before this")
    }

    fun contains(key: Int): Pair<Boolean, List<Int>> {
        val tried = mutableListOf<Int>()
        for (slot in probe(key)) {
            tried.add(slot)
            if (slots[slot] == null) return false to tried
            if (slots[slot] == key) return true to tried
        }
        return false to tried
    }

    fun remove(key: Int, tombstone: Boolean = true) {
        val slot = probe(key).firstOrNull { slots[it] == key } ?: return
        slots[slot] = if (tombstone) DELETED else null
    }
}

fun main() {
    val table = ProbingSet()
    for (key in listOf(3, 11, 19, 6)) {
        println("add %2d: home %d, tried slots %s".format(key, key % SLOTS, table.add(key)))
    }
    println("slots: ${table.slots.contentToString()}")

    table.remove(11)
    println("remove 11 with a tombstone: ${table.slots.contentToString()}")
    println("contains 19? ${table.contains(19)}")

    val broken = ProbingSet()
    for (key in listOf(3, 11, 19)) broken.add(key)
    broken.remove(11, tombstone = false)
    println("remove 11 by emptying its slot, contains 19? ${broken.contains(19)}")
}
