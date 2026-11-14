import java.util.*;

public class Solution {
    public int canCompleteCircuit(int[] gas, int[] cost) {
        // balance is the fuel after driving from station 0 past `station` (it may go negative).
        // Starting right after the station where it is lowest lifts every point of the trip to
        // at least zero, provided the whole circle does not lose fuel.
        int balance = 0;
        int lowest = 0;
        int start = 0;
        for (int station = 0; station < gas.length; station++) {
            balance += gas[station] - cost[station];
            if (balance < lowest) {
                lowest = balance;
                start = station + 1;
            }
        }
        return balance < 0 ? -1 : start % gas.length;
    }
}
