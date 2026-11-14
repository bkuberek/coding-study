import java.util.*;

public class Solution {
    public int[][] intervalIntersection(int[][] firstList, int[][] secondList) {
        List<int[]> common = new ArrayList<>();
        for (int[] first : firstList) {
            int partner = firstEndingAtOrAfter(secondList, first[0]);
            while (partner < secondList.length && secondList[partner][0] <= first[1]) {
                int[] second = secondList[partner];
                common.add(new int[] {Math.max(first[0], second[0]), Math.min(first[1], second[1])});
                partner++;
            }
        }
        return common.toArray(new int[0][]);
    }

    private static int firstEndingAtOrAfter(int[][] intervals, int time) {
        int low = 0;
        int high = intervals.length;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (intervals[middle][1] >= time) {
                high = middle;
            } else {
                low = middle + 1;
            }
        }
        return low;
    }
}
