/**
 * One address space: a page table from page to frame, an optional TLB kept in least-recently-used
 * order, and, once demand paging is on, a frame table with the state each replacement policy
 * needs: the load order for FIFO, the use order for LRU, and a use bit per frame and a hand for
 * the clock. Every translation is one reference in a history, which the working set reads.
 *
 * Splitting an address is a shift and a mask, because the page size is a power of two.
 */
class VirtualMemory(pageSize: Int) {
    private val size = pageSize.toLong()
    private val shift = Integer.numberOfTrailingZeros(pageSize)
    private val table = HashMap<Long, Long>()
    private var faultCount = 0
    private var tlb: LinkedHashMap<Long, Long>? = null
    private var tlbEntries = 0
    private var hits = 0
    private var misses = 0
    private var frames = 0
    private var policy = ""
    private var owner = LongArray(0)
    private val loaded = LinkedHashSet<Long>()
    private val recent = LinkedHashSet<Long>()
    private var use = BooleanArray(0)
    private var hand = 0
    private val history = ArrayList<Long>()

    // Level 1
    fun split(address: Long): LongArray = longArrayOf(address shr shift, address and (size - 1))

    fun mapPage(page: Long, frame: Long): Boolean {
        val isNew = table.put(page, frame) == null
        tlb?.remove(page)
        return isNew
    }

    fun unmapPage(page: Long): Boolean {
        if (table.remove(page) == null) return false
        tlb?.remove(page)
        return true
    }

    fun translate(address: Long): Long {
        val page = address shr shift
        history.add(page)
        val frame = frameOf(page) ?: return -1
        return frame * size + (address and (size - 1))
    }

    fun faults(): Int = faultCount

    // Level 2
    fun enableTlb(entries: Int) {
        tlb = LinkedHashMap(16, 0.75f, true)
        tlbEntries = entries
        hits = 0
        misses = 0
    }

    fun flushTlb() {
        tlb?.clear()
    }

    fun tlbHits(): Int = hits

    fun tlbMisses(): Int = misses

    // Level 3
    fun useFrames(count: Int, policy: String) {
        frames = count
        this.policy = policy
        table.clear()
        flushTlb()
        faultCount = 0
        hits = 0
        misses = 0
        owner = LongArray(count)
        use = BooleanArray(count)
        loaded.clear()
        recent.clear()
        hand = 0
        history.clear()
    }

    fun resident(): LongArray = table.keys.sorted().toLongArray()

    // Level 4
    fun walk(address: Long, entryBytes: Int): LongArray {
        val perTable = size / entryBytes
        val page = address shr shift
        return longArrayOf(page / perTable, page % perTable, address and (size - 1))
    }

    fun tableBytes(addressBits: Int, entryBytes: Int): LongArray {
        val pages = 1L shl (addressBits - shift)
        val perTable = size / entryBytes
        val directory = pages / perTable * entryBytes
        val tables = table.keys.map { it / perTable }.toSet().size
        return longArrayOf(pages * entryBytes, directory + tables * size)
    }

    fun workingSet(window: Int): LongArray = history.takeLast(window).toSortedSet().toLongArray()

    fun thrashing(window: Int): Boolean = frames > 0 && workingSet(window).size > frames

    // Translation
    private fun frameOf(page: Long): Long? {
        val cache = tlb
        if (cache != null) {
            val cached = cache[page]
            if (cached != null) {
                hits++
                touch(page)
                return cached
            }
            misses++
        }
        var frame = table[page]
        if (frame == null) {
            faultCount++
            if (frames == 0) return null
            frame = load(page)
        }
        touch(page)
        if (cache != null) {
            if (cache.size == tlbEntries) cache.remove(cache.keys.first())
            cache[page] = frame
        }
        return frame
    }

    private fun touch(page: Long) {
        if (frames == 0) return
        recent.remove(page)
        recent.add(page)
        use[table.getValue(page).toInt()] = true
    }

    private fun load(page: Long): Long {
        val frame: Int
        if (table.size < frames) {
            frame = table.size
        } else {
            frame = victimFrame()
            val victim = owner[frame]
            table.remove(victim)
            loaded.remove(victim)
            recent.remove(victim)
            tlb?.remove(victim)
        }
        table[page] = frame.toLong()
        owner[frame] = page
        loaded.add(page)
        return frame.toLong()
    }

    private fun victimFrame(): Int {
        when (policy) {
            "fifo" -> return table.getValue(loaded.first()).toInt()
            "lru" -> return table.getValue(recent.first()).toInt()
        }
        while (use[hand]) {
            use[hand] = false
            hand = (hand + 1) % frames
        }
        val frame = hand
        hand = (hand + 1) % frames
        return frame
    }
}
