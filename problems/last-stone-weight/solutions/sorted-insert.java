import java.util.*;

public class Solution {
    public int lastStoneWeight(int[] stones) {
        List<Integer> remaining = new ArrayList<>();
        for (int weight : stones) {
            remaining.add(weight);
        }
        Collections.sort(remaining);
        while (remaining.size() > 1) {
            int heaviest = remaining.remove(remaining.size() - 1);
            int second = remaining.remove(remaining.size() - 1);
            if (heaviest != second) {
                int stone = heaviest - second;
                // binarySearch returns -(insertion point) - 1 when the value is absent.
                int index = Collections.binarySearch(remaining, stone);
                remaining.add(index >= 0 ? index : -index - 1, stone);
            }
        }
        return remaining.isEmpty() ? 0 : remaining.get(0);
    }
}
