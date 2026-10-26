import java.util.*;

public class Solution {
    public boolean canFinish(int numCourses, int[][] prerequisites) {
        List<List<Integer>> unlocks = new ArrayList<>(numCourses);
        for (int course = 0; course < numCourses; course++) {
            unlocks.add(new ArrayList<>());
        }
        int[] waiting = new int[numCourses]; // prerequisites each course still waits for
        for (int[] pair : prerequisites) {
            unlocks.get(pair[1]).add(pair[0]);
            waiting[pair[0]]++;
        }
        ArrayDeque<Integer> ready = new ArrayDeque<>();
        for (int course = 0; course < numCourses; course++) {
            if (waiting[course] == 0) {
                ready.add(course);
            }
        }
        int taken = 0;
        while (!ready.isEmpty()) {
            int course = ready.poll();
            taken++;
            for (int unlocked : unlocks.get(course)) {
                if (--waiting[unlocked] == 0) {
                    ready.add(unlocked);
                }
            }
        }
        // Courses never taken wait, directly or not, on a cycle.
        return taken == numCourses;
    }
}
