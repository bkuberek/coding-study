import java.util.*;

public class Solution {
    public int[] dailyTemperatures(int[] temperatures) {
        int days = temperatures.length;
        int[] waits = new int[days];
        for (int day = 0; day < days; day++) {
            for (int later = day + 1; later < days; later++) {
                if (temperatures[later] > temperatures[day]) {
                    waits[day] = later - day;
                    break;
                }
            }
        }
        return waits;
    }
}
