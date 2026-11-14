import java.util.*;

public class RandomizedSet {
    private final List<Integer> values = new ArrayList<>();
    private final Random random = new Random();

    public RandomizedSet() {
    }

    public boolean insert(int value) {
        // contains is a linear scan using equals: O(n) per call.
        if (values.contains(value)) {
            return false;
        }
        values.add(value);
        return true;
    }

    public boolean remove(int value) {
        // indexOf(Object): the int is boxed, so this searches for the value, not a position.
        int index = values.indexOf(value);
        if (index == -1) {
            return false;
        }
        // Order does not matter: move the last value into the gap instead of shifting.
        int last = values.remove(values.size() - 1);
        if (index < values.size()) {
            values.set(index, last);
        }
        return true;
    }

    public int getRandom() {
        return values.get(random.nextInt(values.size()));
    }
}
