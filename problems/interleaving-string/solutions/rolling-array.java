import java.util.*;

public class Solution {
    public boolean isInterleave(String s1, String s2, String s3) {
        if (s1.length() + s2.length() != s3.length()) {
            return false;
        }
        // Swapping the sources does not change the answer, so let the row run along the shorter.
        boolean firstIsLonger = s1.length() >= s2.length();
        String longer = firstIsLonger ? s1 : s2;
        String shorter = firstIsLonger ? s2 : s1;
        // Before row i is processed, reach[j] tells whether longer[:i - 1] and shorter[:j]
        // interleave to s3[:i - 1 + j]; afterwards it holds row i.
        boolean[] reach = new boolean[shorter.length() + 1];
        for (int i = 0; i <= longer.length(); i++) {
            for (int j = 0; j <= shorter.length(); j++) {
                if (i == 0 && j == 0) {
                    reach[j] = true;
                    continue;
                }
                boolean fromLonger = i > 0 && reach[j] && longer.charAt(i - 1) == s3.charAt(i + j - 1);
                boolean fromShorter = j > 0 && reach[j - 1] && shorter.charAt(j - 1) == s3.charAt(i + j - 1);
                reach[j] = fromLonger || fromShorter;
            }
        }
        return reach[shorter.length()];
    }
}
