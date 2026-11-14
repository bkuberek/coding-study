import java.util.*;

/**
 * The heap is a list of blocks in address order, each with its start, its size (header included)
 * and whether it is in use. Allocating splits a free block; freeing marks it free and, with
 * coalescing or in the buddy system, merges it with its free neighbors. Next fit keeps a rover: the
 * address where its next search starts.
 */
public class MemoryAllocator {
    private static final int HEADER = 8;
    private static final int ALIGN = 8;
    private static final int MIN_BLOCK = 16;
    private static final List<String> POLICIES = List.of("first-fit", "next-fit", "best-fit");

    private static final class Block {
        int start;
        int size;
        boolean used;
        int requested;

        Block(int start, int size) {
            this.start = start;
            this.size = size;
        }
    }

    private final int heapSize;
    private final List<Block> blocks = new ArrayList<>();
    private boolean coalescing = false;
    private String policy = "first-fit";
    private boolean started = false;
    private int rover = 0;

    public MemoryAllocator(int heapSize) {
        this.heapSize = heapSize;
        blocks.add(new Block(0, heapSize));
    }

    // --- helpers
    private int position(int start) {
        for (int i = 0; i < blocks.size(); i++) {
            if (blocks.get(i).start == start) {
                return i;
            }
        }
        return -1;
    }

    private int blockSize(int size) {
        if (policy.equals("buddy")) {
            int block = MIN_BLOCK;
            while (block < size + HEADER) {
                block *= 2;
            }
            return block;
        }
        return HEADER + (size + ALIGN - 1) / ALIGN * ALIGN;
    }

    /** The position of the free block the policy picks, or -1. */
    private int choose(int need) {
        List<Integer> fits = new ArrayList<>();
        for (int i = 0; i < blocks.size(); i++) {
            if (!blocks.get(i).used && blocks.get(i).size >= need) {
                fits.add(i);
            }
        }
        if (fits.isEmpty()) {
            return -1;
        }
        if (policy.equals("next-fit")) {
            int here = position(rover);
            for (int i : fits) {
                if (i >= here) {
                    return i;
                }
            }
            return fits.get(0);
        }
        if (policy.equals("best-fit") || policy.equals("buddy")) {
            int best = fits.get(0);
            for (int i : fits) {
                if (blocks.get(i).size < blocks.get(best).size) {
                    best = i;
                }
            }
            return best;
        }
        return fits.get(0);
    }

    private void split(int position, int keep) {
        Block block = blocks.get(position);
        blocks.add(position + 1, new Block(block.start + keep, block.size - keep));
        block.size = keep;
    }

    private void mergeWithNext(int position) {
        Block block = blocks.get(position);
        Block following = blocks.remove(position + 1);
        block.size += following.size;
        if (rover == following.start) {
            rover = block.start;
        }
    }

    private void freeBuddies(int position) {
        while (blocks.get(position).size < heapSize) {
            Block block = blocks.get(position);
            int other = position(block.start ^ block.size);
            if (other < 0 || blocks.get(other).used || blocks.get(other).size != block.size) {
                return;
            }
            position = Math.min(position, other);
            mergeWithNext(position);
        }
    }

    // Level 1
    public int allocate(int size) {
        started = true;
        int need = blockSize(size);
        int position = choose(need);
        if (position < 0) {
            return -1;
        }
        if (policy.equals("buddy")) {
            while (blocks.get(position).size > need) {
                split(position, blocks.get(position).size / 2);
            }
        } else if (blocks.get(position).size - need >= MIN_BLOCK) {
            split(position, need);
        }
        Block block = blocks.get(position);
        block.used = true;
        block.requested = size;
        rover = (block.start + block.size) % heapSize;
        return block.start + HEADER;
    }

    public String free(int address) {
        int position = position(address - HEADER);
        if (position < 0 || !blocks.get(position).used) {
            return "invalid";
        }
        blocks.get(position).used = false;
        if (policy.equals("buddy")) {
            freeBuddies(position);
        } else if (coalescing) {
            if (position + 1 < blocks.size() && !blocks.get(position + 1).used) {
                mergeWithNext(position);
            }
            if (position > 0 && !blocks.get(position - 1).used) {
                mergeWithNext(position - 1);
            }
        }
        return "ok";
    }

    public List<String> heapMap() {
        List<String> lines = new ArrayList<>();
        for (Block block : blocks) {
            lines.add(block.start + " " + block.size + (block.used ? " used" : " free"));
        }
        return lines;
    }

    // Level 2
    public String setCoalescing(boolean enabled) {
        if (started) {
            return "too-late";
        }
        coalescing = enabled;
        return "ok";
    }

    public List<Integer> freeReport() {
        int count = 0;
        int total = 0;
        int largest = 0;
        for (Block block : blocks) {
            if (!block.used) {
                count++;
                total += block.size;
                largest = Math.max(largest, block.size);
            }
        }
        int fragmentation = total == 0 ? 0 : (int) (100L * (total - largest) / total);
        return List.of(count, total, largest, fragmentation);
    }

    // Level 3
    public String setPolicy(String policy) {
        if (!POLICIES.contains(policy) && !policy.equals("buddy")) {
            return "unknown-policy";
        }
        if (started) {
            return "too-late";
        }
        if (policy.equals("buddy") && (heapSize & (heapSize - 1)) != 0) {
            return "bad-size";
        }
        this.policy = policy;
        return "ok";
    }

    public List<List<Integer>> compare(List<Integer> trace) {
        List<List<Integer>> rows = new ArrayList<>();
        for (String name : POLICIES) {
            MemoryAllocator heap = new MemoryAllocator(heapSize);
            heap.setCoalescing(coalescing);
            heap.setPolicy(name);
            List<Integer> addresses = new ArrayList<>();
            int failed = 0;
            for (int step : trace) {
                if (step > 0) {
                    int address = heap.allocate(step);
                    addresses.add(address);
                    if (address < 0) {
                        failed++;
                    }
                } else if (addresses.get(-step - 1) >= 0) {
                    heap.free(addresses.get(-step - 1));
                }
            }
            List<Integer> row = new ArrayList<>();
            row.add(failed);
            row.addAll(heap.freeReport());
            rows.add(row);
        }
        return rows;
    }

    // Level 4
    public int wasted() {
        int total = 0;
        for (Block block : blocks) {
            if (block.used) {
                total += block.size - HEADER - block.requested;
            }
        }
        return total;
    }
}
