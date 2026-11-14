import java.util.*;

public class Solution {
    private static final int ON_PATH = -1; // marks a course whose chain length is still being computed

    public int minimumSemesters(int n, int[][] relations) {
        List<List<Integer>> required = new ArrayList<>(n + 1);
        for (int course = 0; course <= n; course++) {
            required.add(new ArrayList<>());
        }
        for (int[] relation : relations) {
            required.get(relation[1]).add(relation[0]);
        }
        // chain[c]: courses on the longest prerequisite chain ending at c; 0 = not computed yet.
        int[] chain = new int[n + 1];
        int semesters = 0;
        for (int course = 1; course <= n; course++) {
            int length = chainLength(course, required, chain);
            if (length < 0) {
                return -1;
            }
            semesters = Math.max(semesters, length);
        }
        return semesters;
    }

    // Longest chain ending at course, or -1 if its prerequisites loop.
    private int chainLength(int course, List<List<Integer>> required, int[] chain) {
        if (chain[course] == ON_PATH) {
            return -1;
        }
        if (chain[course] > 0) {
            return chain[course];
        }
        chain[course] = ON_PATH;
        int longest = 0;
        for (int before : required.get(course)) {
            int length = chainLength(before, required, chain);
            if (length < 0) {
                return -1;
            }
            longest = Math.max(longest, length);
        }
        chain[course] = longest + 1;
        return chain[course];
    }
}
