private const val COUNTED = 0
private const val DUPLICATE = 1
private const val RIVAL = 2
private const val LOOP = 3
private const val NONE = -1

/** A growable array of ints, so that a million people do not become a million boxed integers. */
private class Ints {
    private var values = IntArray(16)
    private var length = 0

    operator fun get(at: Int): Int = values[at]

    operator fun set(at: Int, value: Int) {
        values[at] = value
    }

    fun add(value: Int) {
        if (length == values.size) {
            values = values.copyOf(length * 2)
        }
        values[length++] = value
    }
}

/**
 * Counted referrals form a forest: a person has at most one referrer.
 *
 * People are numbered in the order they first appear in a counted referral. The forest is kept in
 * arrays (a referrer, a first and a last child, and a next sibling per person), a union-find
 * answers "would this referral close a loop?" without walking up, and the totals are recounted in
 * one breadth-first pass when a question needs them after a change. Nothing recurses, so a chain
 * of 10^6 referrals is as safe as a flat one.
 */
class ReferralProgram(private val bonus: Int) {
    private val index = HashMap<String, Int>()
    private val names = ArrayList<String>()
    private val referrer = Ints()
    private val first = Ints()
    private val last = Ints()
    private val next = Ints()
    private val direct = Ints()
    private val parentSet = Ints()
    private val setSize = Ints()
    private var totals = IntArray(0)
    private var totalsFresh = true

    // Level 1
    fun refer(referrer: String, referred: String): Int =
        if (apply(referrer, referred) == COUNTED) bonus else 0

    fun points(person: String): Int {
        val at = index[person] ?: return 0
        return direct[at] * bonus
    }

    fun referralsOf(person: String): List<String> {
        val found = mutableListOf<String>()
        var child = index[person]?.let { first[it] } ?: NONE
        while (child != NONE) {
            found.add(names[child])
            child = next[child]
        }
        return found
    }

    // Level 2
    fun totalReferrals(person: String): Int {
        val at = index[person] ?: return 0
        return recount()[at]
    }

    fun topReferrer(): String = leaderboard(1).firstOrNull() ?: ""

    // Level 3
    fun referAll(rows: List<List<String>>): List<Int> {
        val tally = IntArray(4)
        for (row in rows) {
            tally[apply(row[0], row[1])]++
        }
        return tally.toList()
    }

    // Level 4
    fun leaderboard(k: Int): List<String> {
        val counts = recount()
        val ranked = (counts.indices).filter { counts[it] > 0 }.sortedWith(
            compareBy<Int>({ -counts[it] }, { -direct[it] }, { names[it] }),
        )
        return ranked.take(k).map { names[it] }
    }

    private fun person(name: String): Int {
        index[name]?.let { return it }
        val at = names.size
        index[name] = at
        names.add(name)
        referrer.add(NONE)
        first.add(NONE)
        last.add(NONE)
        next.add(NONE)
        direct.add(0)
        parentSet.add(at)
        setSize.add(1)
        totalsFresh = false
        return at
    }

    private fun rootOf(start: Int): Int {
        var at = start
        while (parentSet[at] != at) {
            parentSet[at] = parentSet[parentSet[at]]
            at = parentSet[at]
        }
        return at
    }

    private fun apply(referrerName: String, referredName: String): Int {
        if (referrerName == referredName) {
            return LOOP
        }
        val known = index[referredName]
        if (known != null && referrer[known] != NONE) {
            return if (names[referrer[known]] == referrerName) DUPLICATE else RIVAL
        }
        val above = person(referrerName)
        val below = person(referredName)
        var top = rootOf(above)
        var bottom = rootOf(below)
        if (top == bottom) {
            return LOOP
        }
        if (setSize[top] < setSize[bottom]) {
            val swap = top
            top = bottom
            bottom = swap
        }
        parentSet[bottom] = top
        setSize[top] = setSize[top] + setSize[bottom]
        referrer[below] = above
        if (first[above] == NONE) {
            first[above] = below
        } else {
            next[last[above]] = below
        }
        last[above] = below
        direct[above] = direct[above] + 1
        totalsFresh = false
        return COUNTED
    }

    private fun recount(): IntArray {
        if (totalsFresh) {
            return totals
        }
        val count = names.size
        val order = IntArray(count)
        var filled = 0
        for (at in 0 until count) {
            if (referrer[at] == NONE) {
                order[filled++] = at
            }
        }
        var seen = 0
        while (seen < filled) {
            var child = first[order[seen]]
            while (child != NONE) {
                order[filled++] = child
                child = next[child]
            }
            seen++
        }
        val counted = IntArray(count)
        for (back in filled - 1 downTo 0) {
            val above = referrer[order[back]]
            if (above != NONE) {
                counted[above] += counted[order[back]] + 1
            }
        }
        totals = counted
        totalsFresh = true
        return counted
    }
}
