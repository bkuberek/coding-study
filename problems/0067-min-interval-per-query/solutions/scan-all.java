public class Solution {
    public int[] minInterval(int[][] intervals, int[] queries) {
        int[] answer = new int[queries.length];
        for (int j = 0; j < queries.length; j++) {
            int best = Integer.MAX_VALUE;
            for (int[] interval : intervals) {
                if (interval[0] <= queries[j] && queries[j] <= interval[1]) {
                    best = Math.min(best, interval[1] - interval[0] + 1);
                }
            }
            answer[j] = best == Integer.MAX_VALUE ? -1 : best;
        }
        return answer;
    }
}
