import java.util.*;

public class Solution {
    public int getImportance(int[][] employees, int employeeId) {
        Map<Integer, int[]> byId = new HashMap<>();
        for (int[] record : employees) {
            byId.put(record[0], record);
        }
        int total = 0;
        ArrayDeque<Integer> pending = new ArrayDeque<>();
        pending.push(employeeId);
        while (!pending.isEmpty()) {
            int[] record = byId.get(pending.pop());
            total += record[1];
            // Subordinates start at index 2 of the record.
            for (int i = 2; i < record.length; i++) {
                pending.push(record[i]);
            }
        }
        return total;
    }
}
