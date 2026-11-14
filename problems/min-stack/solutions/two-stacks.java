import java.util.*;

public class MinStack {
    private final Deque<Integer> values = new ArrayDeque<>();
    // The minimums in the order they took effect; the top is the current minimum.
    private final Deque<Integer> minimums = new ArrayDeque<>();

    public MinStack() {
    }

    public void push(int value) {
        values.push(value);
        // <= keeps one copy per equal minimum, so popping one copy keeps the others.
        if (minimums.isEmpty() || value <= minimums.peek()) {
            minimums.push(value);
        }
    }

    public void pop() {
        // Unbox to int before comparing: two Integer objects compared with == are compared
        // by reference, which fails for values outside the small-integer cache.
        int value = values.pop();
        if (value == minimums.peek()) {
            minimums.pop();
        }
    }

    public int top() {
        return values.peek();
    }

    public int getMin() {
        return minimums.peek();
    }
}
