import java.util.*;

public class Solution {
    public int[][] kClosest(int[][] points, int k) {
        int[][] sorted = points.clone();
        // Squared distances order points exactly like distances, without square roots.
        Arrays.sort(sorted, Comparator.comparingInt(point -> point[0] * point[0] + point[1] * point[1]));
        return Arrays.copyOf(sorted, k);
    }
}
