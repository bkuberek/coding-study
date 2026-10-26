import java.util.*;

public class RandomizedSet {
    private final Set<Integer> values = new HashSet<>();
    private final Random random = new Random();

    public RandomizedSet() {
    }

    public boolean insert(int value) {
        // add returns false when the value is already present.
        return values.add(value);
    }

    public boolean remove(int value) {
        // remove(Object) returns whether the value was present.
        return values.remove(value);
    }

    public int getRandom() {
        // A HashSet has no positions: walk its iteration order to a random rank, O(n).
        int rank = random.nextInt(values.size());
        Iterator<Integer> iterator = values.iterator();
        for (int i = 0; i < rank; i++) {
            iterator.next();
        }
        return iterator.next();
    }
}
