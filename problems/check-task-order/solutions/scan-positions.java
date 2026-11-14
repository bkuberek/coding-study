public class Solution {
    public boolean isValidTaskOrder(int n, int[][] prerequisites, int[] order) {
        if (order.length != n) {
            return false;
        }
        for (int task = 0; task < n; task++) {
            if (occurrences(order, task) != 1) {
                return false;
            }
        }
        for (int[] pair : prerequisites) {
            if (indexOf(order, pair[0]) >= indexOf(order, pair[1])) {
                return false;
            }
        }
        return true;
    }

    private int occurrences(int[] order, int task) {
        int count = 0;
        for (int listed : order) {
            if (listed == task) {
                count++;
            }
        }
        return count;
    }

    private int indexOf(int[] order, int task) {
        for (int place = 0; place < order.length; place++) {
            if (order[place] == task) {
                return place;
            }
        }
        return -1;
    }
}
