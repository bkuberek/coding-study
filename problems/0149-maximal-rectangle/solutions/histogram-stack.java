import java.util.*;

public class Solution {
    public int maximalRectangle(char[][] matrix) {
        int columns = matrix[0].length;
        // heights[c] counts the consecutive ones in column c ending at the current row.
        int[] heights = new int[columns];
        int[] rising = new int[columns + 1];
        int best = 0;
        for (char[] row : matrix) {
            for (int c = 0; c < columns; c++) {
                heights[c] = row[c] == '1' ? heights[c] + 1 : 0;
            }
            best = Math.max(best, largestInHistogram(heights, rising));
        }
        return best;
    }

    private static int largestInHistogram(int[] heights, int[] rising) {
        int best = 0;
        // rising[0 .. size) holds indexes of bars whose heights strictly increase from bottom to top.
        int size = 0;
        // One extra bar of height 0 at the end pops every bar still waiting.
        for (int index = 0; index <= heights.length; index++) {
            int height = index < heights.length ? heights[index] : 0;
            while (size > 0 && heights[rising[size - 1]] >= height) {
                int top = rising[--size];
                int left = size > 0 ? rising[size - 1] : -1;
                best = Math.max(best, heights[top] * (index - left - 1));
            }
            rising[size++] = index;
        }
        return best;
    }
}
