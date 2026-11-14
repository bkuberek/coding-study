import java.util.*;

/**
 * One address space: a page table from page to frame, an optional TLB kept in least-recently-used
 * order, and, once demand paging is on, a frame table with the state each replacement policy
 * needs: the load order for FIFO, the use order for LRU, and a use bit per frame and a hand for
 * the clock. Every translation is one reference in a history, which the working set reads.
 *
 * <p>Splitting an address is a shift and a mask, because the page size is a power of two.
 */
public class VirtualMemory {
    private final long size;
    private final int shift;
    private final Map<Long, Long> table = new HashMap<>();
    private int faultCount;
    private LinkedHashMap<Long, Long> tlb;
    private int tlbEntries;
    private int hits;
    private int misses;
    private int frames;
    private String policy = "";
    private long[] owner = new long[0];
    private final LinkedHashSet<Long> loaded = new LinkedHashSet<>();
    private final LinkedHashSet<Long> recent = new LinkedHashSet<>();
    private boolean[] use = new boolean[0];
    private int hand;
    private final List<Long> history = new ArrayList<>();

    public VirtualMemory(int pageSize) {
        size = pageSize;
        shift = Integer.numberOfTrailingZeros(pageSize);
    }

    // Level 1
    public long[] split(long address) {
        return new long[] {address >> shift, address & (size - 1)};
    }

    public boolean mapPage(long page, long frame) {
        boolean isNew = table.put(page, frame) == null;
        invalidate(page);
        return isNew;
    }

    public boolean unmapPage(long page) {
        if (table.remove(page) == null) return false;
        invalidate(page);
        return true;
    }

    public long translate(long address) {
        long page = address >> shift;
        history.add(page);
        Long frame = frameOf(page);
        return frame == null ? -1 : frame * size + (address & (size - 1));
    }

    public int faults() {
        return faultCount;
    }

    // Level 2
    public void enableTlb(int entries) {
        tlb = new LinkedHashMap<>(16, 0.75f, true);
        tlbEntries = entries;
        hits = 0;
        misses = 0;
    }

    public void flushTlb() {
        if (tlb != null) tlb.clear();
    }

    public int tlbHits() {
        return hits;
    }

    public int tlbMisses() {
        return misses;
    }

    // Level 3
    public void useFrames(int count, String policy) {
        frames = count;
        this.policy = policy;
        table.clear();
        flushTlb();
        faultCount = 0;
        hits = 0;
        misses = 0;
        owner = new long[count];
        use = new boolean[count];
        loaded.clear();
        recent.clear();
        hand = 0;
        history.clear();
    }

    public long[] resident() {
        return table.keySet().stream().mapToLong(Long::longValue).sorted().toArray();
    }

    // Level 4
    public long[] walk(long address, int entryBytes) {
        long perTable = size / entryBytes;
        long page = address >> shift;
        return new long[] {page / perTable, page % perTable, address & (size - 1)};
    }

    public long[] tableBytes(int addressBits, int entryBytes) {
        long pages = 1L << (addressBits - shift);
        long perTable = size / entryBytes;
        long directory = pages / perTable * entryBytes;
        Set<Long> tables = new HashSet<>();
        for (long page : table.keySet()) tables.add(page / perTable);
        return new long[] {pages * entryBytes, directory + tables.size() * size};
    }

    public long[] workingSet(int window) {
        List<Long> last = history.subList(Math.max(0, history.size() - window), history.size());
        return new TreeSet<>(last).stream().mapToLong(Long::longValue).toArray();
    }

    public boolean thrashing(int window) {
        return frames > 0 && workingSet(window).length > frames;
    }

    // Translation
    private Long frameOf(long page) {
        if (tlb != null) {
            Long cached = tlb.get(page);
            if (cached != null) {
                hits++;
                touch(page);
                return cached;
            }
            misses++;
        }
        Long frame = table.get(page);
        if (frame == null) {
            faultCount++;
            if (frames == 0) return null;
            frame = load(page);
        }
        touch(page);
        if (tlb != null) {
            if (tlb.size() == tlbEntries) {
                Iterator<Long> oldest = tlb.keySet().iterator();
                oldest.next();
                oldest.remove();
            }
            tlb.put(page, frame);
        }
        return frame;
    }

    private void invalidate(long page) {
        if (tlb != null) tlb.remove(page);
    }

    private void touch(long page) {
        if (frames == 0) return;
        recent.remove(page);
        recent.add(page);
        use[table.get(page).intValue()] = true;
    }

    private long load(long page) {
        int frame;
        if (table.size() < frames) {
            frame = table.size();
        } else {
            frame = victimFrame();
            long victim = owner[frame];
            table.remove(victim);
            loaded.remove(victim);
            recent.remove(victim);
            invalidate(victim);
        }
        table.put(page, (long) frame);
        owner[frame] = page;
        loaded.add(page);
        return frame;
    }

    private int victimFrame() {
        if (policy.equals("fifo")) return table.get(loaded.iterator().next()).intValue();
        if (policy.equals("lru")) return table.get(recent.iterator().next()).intValue();
        while (use[hand]) {
            use[hand] = false;
            hand = (hand + 1) % frames;
        }
        int frame = hand;
        hand = (hand + 1) % frames;
        return frame;
    }
}
