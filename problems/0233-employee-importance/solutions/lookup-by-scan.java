import java.util.*;

public class Solution {
    public int getImportance(int[][] employees, int employeeId) {
        int total = 0;
        ArrayDeque<Integer> pending = new ArrayDeque<>();
        pending.push(employeeId);
        while (!pending.isEmpty()) {
            int wanted = pending.pop();
            int[] record = findRecord(employees, wanted);
            total += record[1];
            for (int i = 2; i < record.length; i++) {
                pending.push(record[i]);
            }
        }
        return total;
    }

    // No index: find the record by scanning the whole list.
    private static int[] findRecord(int[][] employees, int id) {
        for (int[] record : employees) {
            if (record[0] == id) {
                return record;
            }
        }
        throw new IllegalArgumentException("unknown employee " + id);
    }
}
