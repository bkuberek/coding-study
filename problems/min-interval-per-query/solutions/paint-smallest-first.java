import java.util.*;

public class Solution {
    private int[] nextOpen;

    public int[] minInterval(int[][] intervals, int[] queries) {
        int[] points = Arrays.stream(queries).distinct().sorted().toArray();
        int[] sizeAt = new int[points.length];
        Arrays.fill(sizeAt, -1);
        // nextOpen[k]: a link toward the first point at or after k without an answer yet;
        // points.length is a sentinel meaning "none left".
        nextOpen = new int[points.length + 1];
        for (int k = 0; k <= points.length; k++) {
            nextOpen[k] = k;
        }
        int[][] bySize = intervals.clone();
        Arrays.sort(bySize, Comparator.comparingInt(interval -> interval[1] - interval[0]));
        for (int[] interval : bySize) {
            int k = firstOpen(lowerBound(points, interval[0]));
            while (k < points.length && points[k] <= interval[1]) {
                sizeAt[k] = interval[1] - interval[0] + 1;
                nextOpen[k] = k + 1;
                k = firstOpen(k + 1);
            }
        }
        int[] answer = new int[queries.length];
        for (int j = 0; j < queries.length; j++) {
            answer[j] = sizeAt[Arrays.binarySearch(points, queries[j])];
        }
        return answer;
    }

    private int firstOpen(int start) {
        int root = start;
        while (nextOpen[root] != root) {
            root = nextOpen[root];
        }
        int k = start;
        while (nextOpen[k] != root) {
            int next = nextOpen[k];
            nextOpen[k] = root;
            k = next;
        }
        return root;
    }

    private static int lowerBound(int[] sorted, int value) {
        int low = 0;
        int high = sorted.length;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (sorted[middle] < value) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }
}
