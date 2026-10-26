// Debug: Boxed Integer Equality. Some tests fail: find the bug and fix it.
import java.util.*;

public class Solution {
    public List<Integer> changedSkus(List<Integer> before, List<Integer> after) {
        List<Integer> changed = new ArrayList<>();
        for (int i = 0; i < after.size(); i++) {
            Integer previous = i < before.size() ? before.get(i) : null;
            if (previous != after.get(i)) {
                changed.add(i);
            }
        }
        return changed;
    }
}
