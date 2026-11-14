import java.util.*;

public class Solution {
    public int[] dailyTemperatures(int[] temperatures) {
        int[] waits = new int[temperatures.length];
        // Days still waiting for a warmer day, as a stack in a plain array: waiting[0 .. size).
        int[] waiting = new int[temperatures.length];
        int size = 0;
        for (int day = 0; day < temperatures.length; day++) {
            while (size > 0 && temperatures[waiting[size - 1]] < temperatures[day]) {
                int earlier = waiting[--size];
                waits[earlier] = day - earlier;
            }
            waiting[size++] = day;
        }
        return waits;
    }
}
