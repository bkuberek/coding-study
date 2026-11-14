import java.util.*;

public class Solution {
    public int numOfMinutes(int n, int headID, int[] manager, int[] informTime) {
        List<List<Integer>> reports = new ArrayList<>(n);
        for (int employee = 0; employee < n; employee++) {
            reports.add(new ArrayList<>());
        }
        for (int employee = 0; employee < n; employee++) {
            if (manager[employee] != -1) {
                reports.get(manager[employee]).add(employee);
            }
        }
        int longest = 0;
        // Each entry is {employee, minute at which they hear the news}.
        ArrayDeque<int[]> pending = new ArrayDeque<>();
        pending.push(new int[] {headID, 0});
        while (!pending.isEmpty()) {
            int[] entry = pending.pop();
            int employee = entry[0];
            int heardAt = entry[1];
            longest = Math.max(longest, heardAt);
            int passedOnAt = heardAt + informTime[employee];
            for (int report : reports.get(employee)) {
                pending.push(new int[] {report, passedOnAt});
            }
        }
        return longest;
    }
}
