import java.util.*;

public class Solution {
    public List<String> lampPatterns(int n) {
        List<String> result = new ArrayList<>();
        for (int number = 0; number < (1 << n); number++) {
            // Counting up writes the strings in increasing order; the bits are the lamps.
            String bits = Integer.toBinaryString(number);
            String pattern = "0".repeat(n - bits.length()) + bits;
            if (!pattern.contains("11")) {
                result.add(pattern);
            }
        }
        return result;
    }
}
