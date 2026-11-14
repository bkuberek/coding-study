import java.util.*;

public class Solution {
    public int lastStoneWeight(int[] stones) {
        int[] remaining = stones.clone();
        int size = remaining.length;
        // The live stones are remaining[0, size); the two heaviest sit at the end after sorting.
        while (size > 1) {
            Arrays.sort(remaining, 0, size);
            int heaviest = remaining[size - 1];
            int second = remaining[size - 2];
            size -= 2;
            if (heaviest != second) {
                remaining[size++] = heaviest - second;
            }
        }
        return size == 1 ? remaining[0] : 0;
    }
}
