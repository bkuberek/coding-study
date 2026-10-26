import java.util.*;

public class Solution {
    public int minimumSemesters(int n, int[][] relations) {
        List<List<Integer>> unlocks = new ArrayList<>(n + 1);
        for (int course = 0; course <= n; course++) {
            unlocks.add(new ArrayList<>());
        }
        int[] waiting = new int[n + 1];
        for (int[] relation : relations) {
            unlocks.get(relation[0]).add(relation[1]);
            waiting[relation[1]]++;
        }
        List<Integer> semesterCourses = new ArrayList<>();
        for (int course = 1; course <= n; course++) {
            if (waiting[course] == 0) {
                semesterCourses.add(course);
            }
        }
        int semesters = 0;
        int taken = 0;
        while (!semesterCourses.isEmpty()) {
            semesters++;
            taken += semesterCourses.size();
            List<Integer> nextSemester = new ArrayList<>();
            for (int course : semesterCourses) {
                for (int unlocked : unlocks.get(course)) {
                    if (--waiting[unlocked] == 0) {
                        nextSemester.add(unlocked);
                    }
                }
            }
            semesterCourses = nextSemester;
        }
        return taken == n ? semesters : -1;
    }
}
