private const val HEADER = 8
private const val ALIGN = 8
private const val MIN_BLOCK = 16
private val POLICIES = listOf("first-fit", "next-fit", "best-fit")

private class Block(val start: Int, var size: Int) {
    var used = false
    var requested = 0
}

/**
 * The heap is a list of blocks in address order, each with its start, its size (header included)
 * and whether it is in use. Allocating splits a free block; freeing marks it free and, with
 * coalescing or in the buddy system, merges it with its free neighbors. Next fit keeps a rover: the
 * address where its next search starts.
 */
class MemoryAllocator(private val heapSize: Int) {
    private val blocks = mutableListOf(Block(0, heapSize))
    private var coalescing = false
    private var policy = "first-fit"
    private var started = false
    private var rover = 0

    // --- helpers
    private fun position(start: Int): Int = blocks.indexOfFirst { it.start == start }

    private fun blockSize(size: Int): Int {
        if (policy == "buddy") {
            var block = MIN_BLOCK
            while (block < size + HEADER) block *= 2
            return block
        }
        return HEADER + (size + ALIGN - 1) / ALIGN * ALIGN
    }

    /** The position of the free block the policy picks, or -1. */
    private fun choose(need: Int): Int {
        val fits = blocks.indices.filter { !blocks[it].used && blocks[it].size >= need }
        if (fits.isEmpty()) return -1
        return when (policy) {
            "next-fit" -> {
                val here = position(rover)
                fits.firstOrNull { it >= here } ?: fits.first()
            }
            // minBy keeps the first of equal sizes, which is the lowest address.
            "best-fit", "buddy" -> fits.minBy { blocks[it].size }
            else -> fits.first()
        }
    }

    private fun split(position: Int, keep: Int) {
        val block = blocks[position]
        blocks.add(position + 1, Block(block.start + keep, block.size - keep))
        block.size = keep
    }

    private fun mergeWithNext(position: Int) {
        val block = blocks[position]
        val following = blocks.removeAt(position + 1)
        block.size += following.size
        if (rover == following.start) rover = block.start
    }

    private fun freeBuddies(freed: Int) {
        var position = freed
        while (blocks[position].size < heapSize) {
            val block = blocks[position]
            val other = position(block.start xor block.size)
            if (other < 0 || blocks[other].used || blocks[other].size != block.size) return
            position = minOf(position, other)
            mergeWithNext(position)
        }
    }

    // Level 1
    fun allocate(size: Int): Int {
        started = true
        val need = blockSize(size)
        val position = choose(need)
        if (position < 0) return -1
        if (policy == "buddy") {
            while (blocks[position].size > need) split(position, blocks[position].size / 2)
        } else if (blocks[position].size - need >= MIN_BLOCK) {
            split(position, need)
        }
        val block = blocks[position]
        block.used = true
        block.requested = size
        rover = (block.start + block.size) % heapSize
        return block.start + HEADER
    }

    fun free(address: Int): String {
        val position = position(address - HEADER)
        if (position < 0 || !blocks[position].used) return "invalid"
        blocks[position].used = false
        if (policy == "buddy") {
            freeBuddies(position)
        } else if (coalescing) {
            if (position + 1 < blocks.size && !blocks[position + 1].used) mergeWithNext(position)
            if (position > 0 && !blocks[position - 1].used) mergeWithNext(position - 1)
        }
        return "ok"
    }

    fun heapMap(): List<String> =
        blocks.map { "${it.start} ${it.size} ${if (it.used) "used" else "free"}" }

    // Level 2
    fun setCoalescing(enabled: Boolean): String {
        if (started) return "too-late"
        coalescing = enabled
        return "ok"
    }

    fun freeReport(): List<Int> {
        val sizes = blocks.filter { !it.used }.map { it.size }
        val total = sizes.sum()
        val largest = sizes.maxOrNull() ?: 0
        val fragmentation = if (total == 0) 0 else 100 * (total - largest) / total
        return listOf(sizes.size, total, largest, fragmentation)
    }

    // Level 3
    fun setPolicy(policy: String): String {
        if (policy !in POLICIES && policy != "buddy") return "unknown-policy"
        if (started) return "too-late"
        if (policy == "buddy" && (heapSize and (heapSize - 1)) != 0) return "bad-size"
        this.policy = policy
        return "ok"
    }

    fun compare(trace: List<Int>): List<List<Int>> =
        POLICIES.map { name ->
            val heap = MemoryAllocator(heapSize)
            heap.setCoalescing(coalescing)
            heap.setPolicy(name)
            val addresses = mutableListOf<Int>()
            var failed = 0
            for (step in trace) {
                if (step > 0) {
                    val address = heap.allocate(step)
                    addresses.add(address)
                    if (address < 0) failed++
                } else if (addresses[-step - 1] >= 0) {
                    heap.free(addresses[-step - 1])
                }
            }
            listOf(failed) + heap.freeReport()
        }

    // Level 4
    fun wasted(): Int = blocks.filter { it.used }.sumOf { it.size - HEADER - it.requested }
}
