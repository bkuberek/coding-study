import java.util.*;

public class Solution {
    public int canCompleteCircuit(int[] gas, int[] cost) {
        int total = 0; // fuel balance of the whole circle
        int fuel = 0; // fuel since the current candidate start
        int start = 0;
        for (int station = 0; station < gas.length; station++) {
            int surplus = gas[station] - cost[station];
            total += surplus;
            fuel += surplus;
            if (fuel < 0) {
                // No station from `start` to `station` can be the answer; try the next one.
                start = station + 1;
                fuel = 0;
            }
        }
        return total >= 0 ? start : -1;
    }
}
