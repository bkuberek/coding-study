import java.util.*;

public class Solution {
    public int minimumSemesters(int n, int[][] relations) {
        List<List<Integer>> required = new ArrayList<>(n + 1);
        for (int course = 0; course <= n; course++) {
            required.add(new ArrayList<>());
        }
        for (int[] relation : relations) {
            required.get(relation[1]).add(relation[0]);
        }
        int[] finishedIn = new int[n + 1]; // semester a course was taken in; 0 while not taken
        int done = 0;
        int semester = 0;
        while (done < n) {
            semester++;
            // Free courses need every prerequisite finished in an earlier semester.
            List<Integer> free = new ArrayList<>();
            for (int course = 1; course <= n; course++) {
                if (finishedIn[course] == 0 && finishedBefore(required.get(course), finishedIn, semester)) {
                    free.add(course);
                }
            }
            if (free.isEmpty()) {
                return -1;
            }
            for (int course : free) {
                finishedIn[course] = semester;
            }
            done += free.size();
        }
        return semester;
    }

    private static boolean finishedBefore(List<Integer> courses, int[] finishedIn, int semester) {
        for (int course : courses) {
            if (finishedIn[course] == 0 || finishedIn[course] >= semester) {
                return false;
            }
        }
        return true;
    }
}
