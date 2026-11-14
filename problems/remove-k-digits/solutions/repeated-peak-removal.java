import java.util.*;

public class Solution {
    public String removeKDigits(String num, int k) {
        StringBuilder digits = new StringBuilder(num);
        for (int removed = 0; removed < k; removed++) {
            // The first digit larger than its successor, or the last digit if none is.
            int peak = 0;
            while (peak + 1 < digits.length() && digits.charAt(peak) <= digits.charAt(peak + 1)) {
                peak++;
            }
            digits.deleteCharAt(peak);
        }
        int start = 0;
        while (start < digits.length() && digits.charAt(start) == '0') {
            start++;
        }
        return start == digits.length() ? "0" : digits.substring(start);
    }
}
