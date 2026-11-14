import java.util.ArrayList;
import java.util.List;

public class Solution {
    private static final long BASE = 131;
    private static final long MODULUS = 1_000_000_007L;

    public int[] findAllOccurrences(String text, String pattern) {
        int windowSize = pattern.length();
        if (windowSize > text.length()) {
            return new int[0];
        }
        long leavingWeight = 1;
        for (int i = 1; i < windowSize; i++) {
            leavingWeight = leavingWeight * BASE % MODULUS;
        }
        long target = 0;
        long window = 0;
        for (int i = 0; i < windowSize; i++) {
            target = (target * BASE + pattern.charAt(i)) % MODULUS;
            window = (window * BASE + text.charAt(i)) % MODULUS;
        }
        List<Integer> found = new ArrayList<>();
        for (int start = 0; start + windowSize <= text.length(); start++) {
            if (window == target && text.startsWith(pattern, start)) {
                found.add(start);
            }
            if (start + windowSize < text.length()) {
                long without = (window - text.charAt(start) * leavingWeight % MODULUS + MODULUS) % MODULUS;
                window = (without * BASE + text.charAt(start + windowSize)) % MODULUS;
            }
        }
        int[] result = new int[found.size()];
        for (int i = 0; i < result.length; i++) {
            result[i] = found.get(i);
        }
        return result;
    }
}
