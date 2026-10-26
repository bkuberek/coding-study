import java.util.*;

public class Solution {
    public String removeKDigits(String num, int k) {
        // The digits kept so far, used as a stack; they never decrease from bottom to top.
        StringBuilder kept = new StringBuilder(num.length());
        int remaining = k;
        for (int i = 0; i < num.length(); i++) {
            char digit = num.charAt(i);
            while (remaining > 0 && kept.length() > 0 && kept.charAt(kept.length() - 1) > digit) {
                kept.setLength(kept.length() - 1);
                remaining--;
            }
            kept.append(digit);
        }
        // The kept digits never decrease, so leftover deletions are cheapest at the end.
        kept.setLength(kept.length() - remaining);
        int start = 0;
        while (start < kept.length() && kept.charAt(start) == '0') {
            start++;
        }
        return start == kept.length() ? "0" : kept.substring(start);
    }
}
