import java.util.*;

public class Solution {
    public boolean wordBreak(String s, String[] wordDict) {
        Set<String> words = new HashSet<>(Arrays.asList(wordDict));
        int longest = 0;
        for (String word : wordDict) {
            longest = Math.max(longest, word.length());
        }
        // ok[i] is true when the prefix s[0..i) can be split into dictionary words.
        boolean[] ok = new boolean[s.length() + 1];
        ok[0] = true;
        for (int end = 1; end <= s.length(); end++) {
            for (int start = Math.max(0, end - longest); start < end; start++) {
                if (ok[start] && words.contains(s.substring(start, end))) {
                    ok[end] = true;
                    break;
                }
            }
        }
        return ok[s.length()];
    }
}
