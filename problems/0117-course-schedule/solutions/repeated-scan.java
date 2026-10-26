import java.util.*;

public class Solution {
    public boolean canFinish(int numCourses, int[][] prerequisites) {
        List<List<Integer>> required = new ArrayList<>(numCourses);
        for (int course = 0; course < numCourses; course++) {
            required.add(new ArrayList<>());
        }
        for (int[] pair : prerequisites) {
            required.get(pair[0]).add(pair[1]);
        }
        boolean[] taken = new boolean[numCourses];
        for (int round = 0; round < numCourses; round++) {
            // Take the first course whose prerequisites are all done; give up if there is none.
            int next = -1;
            for (int course = 0; course < numCourses && next < 0; course++) {
                if (!taken[course] && allTaken(required.get(course), taken)) {
                    next = course;
                }
            }
            if (next < 0) {
                return false;
            }
            taken[next] = true;
        }
        return true;
    }

    private static boolean allTaken(List<Integer> courses, boolean[] taken) {
        for (int course : courses) {
            if (!taken[course]) {
                return false;
            }
        }
        return true;
    }
}
