import java.util.*;

public class Solution {
    private static final int UNVISITED = 0;
    private static final int ON_PATH = 1;
    private static final int DONE = 2;

    public boolean canFinish(int numCourses, int[][] prerequisites) {
        List<List<Integer>> required = new ArrayList<>(numCourses);
        for (int course = 0; course < numCourses; course++) {
            required.add(new ArrayList<>());
        }
        for (int[] pair : prerequisites) {
            required.get(pair[0]).add(pair[1]);
        }
        int[] state = new int[numCourses];
        for (int course = 0; course < numCourses; course++) {
            if (state[course] == UNVISITED && !completes(course, required, state)) {
                return false;
            }
        }
        return true;
    }

    // Whether every prerequisite chain below course ends without looping.
    private boolean completes(int course, List<List<Integer>> required, int[] state) {
        state[course] = ON_PATH;
        for (int before : required.get(course)) {
            if (state[before] == ON_PATH) {
                return false; // the chain came back to a course still being explored
            }
            if (state[before] == UNVISITED && !completes(before, required, state)) {
                return false;
            }
        }
        state[course] = DONE;
        return true;
    }
}
