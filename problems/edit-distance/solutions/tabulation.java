import java.util.*;

public class Solution {
    public int minDistance(String word1, String word2) {
        int rows = word1.length();
        int columns = word2.length();
        // cost[i][j] is the distance between the prefixes word1[:i] and word2[:j]. Turning a prefix
        // into the empty word takes one deletion per character, and the reverse one insertion.
        int[][] cost = new int[rows + 1][columns + 1];
        for (int i = 0; i <= rows; i++) {
            cost[i][0] = i;
        }
        for (int j = 0; j <= columns; j++) {
            cost[0][j] = j;
        }
        for (int i = 1; i <= rows; i++) {
            for (int j = 1; j <= columns; j++) {
                if (word1.charAt(i - 1) == word2.charAt(j - 1)) {
                    cost[i][j] = cost[i - 1][j - 1];
                } else {
                    cost[i][j] = 1 + Math.min(cost[i - 1][j], Math.min(cost[i][j - 1], cost[i - 1][j - 1]));
                }
            }
        }
        return cost[rows][columns];
    }
}
