import java.util.*;

public class Solution {
    public int canCompleteCircuit(int[] gas, int[] cost) {
        int n = gas.length;
        for (int start = 0; start < n; start++) {
            int fuel = 0;
            int step = 0;
            while (step < n) {
                int station = (start + step) % n;
                fuel += gas[station] - cost[station];
                if (fuel < 0) {
                    break;
                }
                step++;
            }
            if (step == n) {
                return start;
            }
        }
        return -1;
    }
}
