import java.util.*;

public class Solution {
    private static final long MODULUS = 1_000_000_007L;

    public int createSortedArray(int[] instructions) {
        int largest = Arrays.stream(instructions).max().getAsInt();
        // tree[i] (1-based) counts the inserted values in (i - (i & -i), i].
        int[] tree = new int[largest + 1];
        long cost = 0;
        for (int inserted = 0; inserted < instructions.length; inserted++) {
            int value = instructions[inserted];
            int less = countAtMost(tree, value - 1);
            int greater = inserted - countAtMost(tree, value);
            cost = (cost + Math.min(less, greater)) % MODULUS;
            for (int i = value; i <= largest; i += i & -i) {
                tree[i]++;
            }
        }
        return (int) cost;
    }

    private static int countAtMost(int[] tree, int value) {
        int total = 0;
        for (int i = value; i > 0; i -= i & -i) {
            total += tree[i];
        }
        return total;
    }
}
