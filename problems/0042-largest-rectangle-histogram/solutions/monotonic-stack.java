import java.util.*;

public class Solution {
    public int largestRectangleArea(int[] heights) {
        int best = 0;
        // Indexes of bars whose heights strictly increase from bottom to top: rising[0 .. size).
        int[] rising = new int[heights.length + 1];
        int size = 0;
        // One extra bar of height 0 at the end pops every bar still waiting.
        for (int index = 0; index <= heights.length; index++) {
            int height = index < heights.length ? heights[index] : 0;
            while (size > 0 && heights[rising[size - 1]] >= height) {
                int top = rising[--size];
                // The bar below `top` on the stack is lower, and so is `index` (or it is equal and
                // a later pop covers the full width): the rectangle spans the bars between them.
                int left = size > 0 ? rising[size - 1] : -1;
                best = Math.max(best, heights[top] * (index - left - 1));
            }
            rising[size++] = index;
        }
        return best;
    }
}
