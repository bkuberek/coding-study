import java.util.*;

public class MinStack {
    // Each entry is {value, minimum of this value and everything below it}.
    private final Deque<int[]> entries = new ArrayDeque<>();

    public MinStack() {
    }

    public void push(int value) {
        int minimum = entries.isEmpty() ? value : Math.min(value, entries.peek()[1]);
        entries.push(new int[] {value, minimum});
    }

    public void pop() {
        entries.pop();
    }

    public int top() {
        return entries.peek()[0];
    }

    public int getMin() {
        return entries.peek()[1];
    }
}
