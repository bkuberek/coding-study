import java.util.*;

public class Solution {
    public boolean isValidTaskOrder(int n, int[][] prerequisites, int[] order) {
        if (order.length != n) {
            return false;
        }
        // position[t]: where task t stands in the order, or -1 while it has not been seen.
        int[] position = new int[n];
        Arrays.fill(position, -1);
        for (int place = 0; place < order.length; place++) {
            if (position[order[place]] != -1) {
                return false;
            }
            position[order[place]] = place;
        }
        for (int[] pair : prerequisites) {
            if (position[pair[0]] >= position[pair[1]]) {
                return false;
            }
        }
        return true;
    }
}
