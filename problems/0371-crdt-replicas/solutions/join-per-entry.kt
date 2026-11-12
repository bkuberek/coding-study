/** One replica's slot of a counter: what it added and what it took away, each with the change number at which it last grew. */
private class Slot {
    var up = 0L
    var upAt = 0L
    var down = 0L
    var downAt = 0L
}

private class Register(val text: String, val timestamp: Long, val writer: String, val at: Long) {
    fun losesTo(otherTimestamp: Long, otherWriter: String): Boolean =
        if (otherTimestamp != timestamp) otherTimestamp > timestamp else otherWriter > writer
}

private class Tag(val addedAt: Long) {
    var removed = false
    var removedAt = 0L
}

/**
 * The whole state of one replica. Every entry (a counter slot's up or down part, a register, an
 * add tag, a tombstone) only grows, and each one remembers the change number at which it last
 * grew, so a sync can pick the entries that changed after the last acknowledgement.
 */
private class Replica {
    var clock = 0L
    var adds = 0
    val counters = HashMap<String, HashMap<String, Slot>>()
    val registers = HashMap<String, Register>()
    val sets = HashMap<String, HashMap<String, HashMap<String, Tag>>>()
    val acked = HashMap<String, Long>()

    fun tick(): Long = ++clock

    fun slot(counter: String, owner: String): Slot =
        counters.getOrPut(counter) { HashMap() }.getOrPut(owner) { Slot() }

    fun total(counter: String): Int =
        (counters[counter]?.values ?: emptyList()).sumOf { it.up - it.down }.toInt()

    fun tags(setName: String, element: String): HashMap<String, Tag> =
        sets.getOrPut(setName) { HashMap() }.getOrPut(element) { HashMap() }

    fun live(setName: String, element: String): Boolean =
        sets[setName]?.get(element)?.values?.any { !it.removed } ?: false

    fun size(): Int {
        val parts = counters.values.flatMap { it.values }.sumOf { (if (it.up > 0) 1 else 0) + (if (it.down > 0) 1 else 0) }
        val tags = sets.values.flatMap { it.values }.flatMap { it.values }.sumOf { if (it.removed) 2 else 1 }
        return parts + registers.size + tags
    }

    /** Joins every entry of [source] that changed after [since]; `since = 0` is a full merge. */
    fun absorb(source: Replica, since: Long): Int {
        var sent = 0
        for ((counter, slots) in source.counters) {
            for ((owner, theirs) in slots) {
                val mine = slot(counter, owner)
                if (theirs.up > 0 && theirs.upAt > since) {
                    sent++
                    if (theirs.up > mine.up) {
                        mine.up = theirs.up
                        mine.upAt = tick()
                    }
                }
                if (theirs.down > 0 && theirs.downAt > since) {
                    sent++
                    if (theirs.down > mine.down) {
                        mine.down = theirs.down
                        mine.downAt = tick()
                    }
                }
            }
        }
        for ((name, theirs) in source.registers) {
            if (theirs.at <= since) continue
            sent++
            val mine = registers[name]
            if (mine == null || mine.losesTo(theirs.timestamp, theirs.writer)) {
                registers[name] = Register(theirs.text, theirs.timestamp, theirs.writer, tick())
            }
        }
        for ((setName, elements) in source.sets) {
            for ((element, tags) in elements) {
                val mine = tags(setName, element)
                for ((tag, theirs) in tags) sent += absorbTag(mine, tag, theirs, since)
            }
        }
        return sent
    }

    private fun absorbTag(mine: HashMap<String, Tag>, tag: String, theirs: Tag, since: Long): Int {
        var sent = 0
        if (theirs.addedAt > since) {
            sent++
            if (tag !in mine) mine[tag] = Tag(tick())
        }
        if (theirs.removed && theirs.removedAt > since) {
            sent++
            val held = mine.getOrPut(tag) { Tag(tick()) }
            if (!held.removed) {
                held.removed = true
                held.removedAt = tick()
            }
        }
        return sent
    }
}

/**
 * A group of replicas of the same data. Each replica's state is a set of entries that only grow,
 * and merging is taking the larger value of every entry, so merges can happen in any order, any
 * number of times, and replicas that have seen the same updates hold the same state.
 */
class Replicas(ids: List<String>) {
    private val replicas = ids.associateWith { Replica() }

    private fun at(name: String): Replica = replicas.getValue(name)

    // Level 1
    fun increment(replica: String, counter: String, amount: Int): Int {
        val node = at(replica)
        val slot = node.slot(counter, replica)
        slot.up += amount
        slot.upAt = node.tick()
        return node.total(counter)
    }

    fun decrement(replica: String, counter: String, amount: Int): Int {
        val node = at(replica)
        val slot = node.slot(counter, replica)
        slot.down += amount
        slot.downAt = node.tick()
        return node.total(counter)
    }

    fun value(replica: String, counter: String): Int = at(replica).total(counter)

    fun merge(source: String, target: String) {
        at(target).absorb(at(source), 0)
    }

    // Level 2
    fun write(replica: String, register: String, text: String, timestamp: Long): Boolean {
        val node = at(replica)
        val current = node.registers[register]
        if (current != null && !current.losesTo(timestamp, replica)) return false
        node.registers[register] = Register(text, timestamp, replica, node.tick())
        return true
    }

    fun read(replica: String, register: String): String = at(replica).registers[register]?.text ?: ""

    // Level 3
    fun add(replica: String, setName: String, element: String): String {
        val node = at(replica)
        node.adds++
        val tag = "$replica:${node.adds}"
        node.tags(setName, element)[tag] = Tag(node.tick())
        return tag
    }

    fun remove(replica: String, setName: String, element: String): Int {
        val node = at(replica)
        val seen = node.sets[setName]?.get(element)?.values?.filter { !it.removed } ?: emptyList()
        for (tag in seen) {
            tag.removed = true
            tag.removedAt = node.tick()
        }
        return seen.size
    }

    fun contains(replica: String, setName: String, element: String): Boolean = at(replica).live(setName, element)

    fun elements(replica: String, setName: String): List<String> {
        val node = at(replica)
        return (node.sets[setName]?.keys ?: emptySet()).filter { node.live(setName, it) }.sorted()
    }

    // Level 4
    fun sync(source: String, target: String): Int {
        val sender = at(source)
        val sent = at(target).absorb(sender, sender.acked[target] ?: 0L)
        sender.acked[target] = sender.clock
        return sent
    }

    fun stateSize(replica: String): Int = at(replica).size()
}
