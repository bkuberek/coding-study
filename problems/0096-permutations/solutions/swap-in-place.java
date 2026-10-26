import java.util.*;

public class Solution {
    public List<List<Integer>> permute(int[] nums) {
        int[] values = nums.clone();
        List<List<Integer>> result = new ArrayList<>();
        fixSlot(values, 0, result);
        return result;
    }

    // values[0..slot-1] is the fixed prefix; values[slot..] are the candidates still free.
    private void fixSlot(int[] values, int slot, List<List<Integer>> result) {
        if (slot == values.length) {
            List<Integer> ordering = new ArrayList<>(values.length);
            for (int value : values) {
                ordering.add(value);
            }
            result.add(ordering);
            return;
        }
        for (int candidate = slot; candidate < values.length; candidate++) {
            swap(values, slot, candidate);
            fixSlot(values, slot + 1, result);
            swap(values, slot, candidate);
        }
    }

    private static void swap(int[] values, int i, int j) {
        int held = values[i];
        values[i] = values[j];
        values[j] = held;
    }
}
