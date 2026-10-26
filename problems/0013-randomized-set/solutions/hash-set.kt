import kotlin.random.Random

class RandomizedSet {
    private val values = HashSet<Int>()

    // add and remove return whether they changed the set.
    fun insert(value: Int): Boolean = values.add(value)

    fun remove(value: Int): Boolean = values.remove(value)

    // A HashSet has no positions: elementAt walks its iteration order to the rank, O(n).
    fun getRandom(): Int = values.elementAt(Random.nextInt(values.size))
}
