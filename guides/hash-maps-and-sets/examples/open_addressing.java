import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

// Open addressing with linear probing: a key that finds its home slot taken tries the next one.
//
// Keys are small integers hashed as `key % 8`, so that the collisions are easy to follow.
public class OpenAddressing {
    static final int SLOTS = 8;
    // A tombstone: the slot is free to reuse, but a search goes on past it.
    static final String DELETED = "<deleted>";

    record Probe(boolean found, List<Integer> tried) {
        @Override
        public String toString() {
            return "(" + found + ", " + tried + ")";
        }
    }

    static final class ProbingSet {
        final Object[] slots = new Object[SLOTS]; // null is an empty slot

        /** The slots to try for `key`: its home slot, then the next ones, wrapping around. */
        int[] probe(int key) {
            int home = key % SLOTS;
            int[] order = new int[SLOTS];
            for (int step = 0; step < SLOTS; step++) {
                order[step] = (home + step) % SLOTS;
            }
            return order;
        }

        List<Integer> add(int key) {
            List<Integer> tried = new ArrayList<>();
            Integer reusable = null;
            for (int slot : probe(key)) {
                tried.add(slot);
                if (Integer.valueOf(key).equals(slots[slot])) {
                    return tried;
                }
                if (DELETED.equals(slots[slot]) && reusable == null) {
                    reusable = slot;
                }
                if (slots[slot] == null) {
                    slots[reusable == null ? slot : reusable] = key;
                    return tried;
                }
            }
            throw new IllegalStateException("full: a real table resizes long before this");
        }

        Probe contains(int key) {
            List<Integer> tried = new ArrayList<>();
            for (int slot : probe(key)) {
                tried.add(slot);
                if (slots[slot] == null) {
                    return new Probe(false, tried);
                }
                if (Integer.valueOf(key).equals(slots[slot])) {
                    return new Probe(true, tried);
                }
            }
            return new Probe(false, tried);
        }

        void remove(int key, boolean tombstone) {
            for (int slot : probe(key)) {
                if (Integer.valueOf(key).equals(slots[slot])) {
                    slots[slot] = tombstone ? DELETED : null;
                    return;
                }
            }
        }
    }

    public static void main(String[] args) {
        ProbingSet table = new ProbingSet();
        for (int key : new int[] {3, 11, 19, 6}) {
            List<Integer> tried = table.add(key);
            System.out.printf("add %2d: home %d, tried slots %s%n", key, key % SLOTS, tried);
        }
        System.out.println("slots: " + Arrays.toString(table.slots));

        table.remove(11, true);
        System.out.println("remove 11 with a tombstone: " + Arrays.toString(table.slots));
        System.out.println("contains 19? " + table.contains(19));

        ProbingSet broken = new ProbingSet();
        for (int key : new int[] {3, 11, 19}) {
            broken.add(key);
        }
        broken.remove(11, false);
        System.out.println("remove 11 by emptying its slot, contains 19? " + broken.contains(19));
    }
}
