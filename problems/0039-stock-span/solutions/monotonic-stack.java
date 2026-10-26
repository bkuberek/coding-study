import java.util.*;

public class StockSpanner {
    // Each entry is {price, span}; prices strictly decrease from bottom to top.
    private final Deque<int[]> stack = new ArrayDeque<>();

    public StockSpanner() {
    }

    public int span(int price) {
        int span = 1;
        while (!stack.isEmpty() && stack.peek()[0] <= price) {
            span += stack.pop()[1];
        }
        stack.push(new int[] {price, span});
        return span;
    }
}
