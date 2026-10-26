import java.util.*;

public class MinStack {
    private final List<Integer> values = new ArrayList<>();

    public MinStack() {
    }

    public void push(int value) {
        values.add(value);
    }

    public void pop() {
        values.remove(values.size() - 1);
    }

    public int top() {
        return values.get(values.size() - 1);
    }

    public int getMin() {
        // Collections.min scans the whole list: O(n) per call.
        return Collections.min(values);
    }
}
