import java.util.*;

public class Solution {
    public int[][] intervalIntersection(int[][] firstList, int[][] secondList) {
        // Both lists are sorted and separate, so pairs taken in this order yield sorted output.
        List<int[]> common = new ArrayList<>();
        for (int[] first : firstList) {
            for (int[] second : secondList) {
                int start = Math.max(first[0], second[0]);
                int end = Math.min(first[1], second[1]);
                if (start <= end) {
                    common.add(new int[] {start, end});
                }
            }
        }
        return common.toArray(new int[0][]);
    }
}
