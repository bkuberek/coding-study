import java.util.*;

public class Solution {
    public boolean isAnagram(String s, String t) {
        if (s.length() != t.length()) {
            return false;
        }
        char[] left = s.toCharArray();
        char[] right = t.toCharArray();
        Arrays.sort(left);
        Arrays.sort(right);
        return Arrays.equals(left, right);
    }
}
