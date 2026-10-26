import java.util.*;

public class RandomizedSet {
    private final List<Integer> values = new ArrayList<>();
    private final Map<Integer, Integer> indexOf = new HashMap<>();
    private final Random random = new Random();

    public RandomizedSet() {
    }

    public boolean insert(int value) {
        if (indexOf.containsKey(value)) {
            return false;
        }
        indexOf.put(value, values.size());
        values.add(value);
        return true;
    }

    public boolean remove(int value) {
        Integer index = indexOf.remove(value);
        if (index == null) {
            return false;
        }
        // remove(int) removes by position; the result unboxes to the former last value.
        int last = values.remove(values.size() - 1);
        if (index < values.size()) {
            // Fill the gap with the former last value and record its new position.
            values.set(index, last);
            indexOf.put(last, index);
        }
        return true;
    }

    public int getRandom() {
        return values.get(random.nextInt(values.size()));
    }
}
