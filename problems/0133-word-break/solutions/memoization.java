import java.util.*;

public class Solution {
    public boolean wordBreak(String s, String[] wordDict) {
        // memo[start] answers "can the suffix s[start..] be split?"; null means not computed.
        return canSplitFrom(0, s, wordDict, new Boolean[s.length()]);
    }

    private boolean canSplitFrom(int start, String s, String[] wordDict, Boolean[] memo) {
        if (start == s.length()) {
            return true;
        }
        if (memo[start] == null) {
            memo[start] = false;
            for (String word : wordDict) {
                if (s.startsWith(word, start)
                        && canSplitFrom(start + word.length(), s, wordDict, memo)) {
                    memo[start] = true;
                    break;
                }
            }
        }
        return memo[start];
    }
}
