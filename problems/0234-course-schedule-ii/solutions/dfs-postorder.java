import java.util.*;

public class Solution {
    private static final int UNSEEN = 0;
    private static final int ACTIVE = 1;
    private static final int DONE = 2;

    public int[] findOrder(int numCourses, int[][] prerequisites) {
        List<List<Integer>> required = new ArrayList<>(numCourses);
        for (int course = 0; course < numCourses; course++) {
            required.add(new ArrayList<>());
        }
        for (int[] pair : prerequisites) {
            required.get(pair[0]).add(pair[1]);
        }
        int[] state = new int[numCourses];
        int[] cursor = new int[numCourses]; // next prerequisite to visit, per course
        int[] order = new int[numCourses];
        int listed = 0;
        for (int root = 0; root < numCourses; root++) {
            if (state[root] != UNSEEN) {
                continue;
            }
            state[root] = ACTIVE;
            ArrayDeque<Integer> stack = new ArrayDeque<>();
            stack.push(root);
            while (!stack.isEmpty()) {
                int course = stack.peek();
                if (cursor[course] == required.get(course).size()) {
                    // Every prerequisite is already in the order: the course can follow them.
                    stack.pop();
                    state[course] = DONE;
                    order[listed++] = course;
                    continue;
                }
                int before = required.get(course).get(cursor[course]++);
                if (state[before] == ACTIVE) {
                    return new int[0]; // the path loops back to a course still being explored
                }
                if (state[before] == UNSEEN) {
                    state[before] = ACTIVE;
                    stack.push(before);
                }
            }
        }
        return order;
    }
}
