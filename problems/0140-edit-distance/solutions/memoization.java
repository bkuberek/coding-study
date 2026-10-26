import java.util.*;

public class Solution {
    private String word1;
    private String word2;
    // cost[i][j] caches the distance between the suffixes word1[i:] and word2[j:]; -1 is unknown.
    private int[][] cost;

    public int minDistance(String word1, String word2) {
        this.word1 = word1;
        this.word2 = word2;
        cost = new int[word1.length() + 1][word2.length() + 1];
        for (int[] row : cost) {
            Arrays.fill(row, -1);
        }
        return solve(0, 0);
    }

    private int solve(int i, int j) {
        if (i == word1.length()) {
            return word2.length() - j; // insert the rest of word2
        }
        if (j == word2.length()) {
            return word1.length() - i; // delete the rest of word1
        }
        if (cost[i][j] < 0) {
            if (word1.charAt(i) == word2.charAt(j)) {
                cost[i][j] = solve(i + 1, j + 1);
            } else {
                int delete = solve(i + 1, j);
                int insert = solve(i, j + 1);
                int replace = solve(i + 1, j + 1);
                cost[i][j] = 1 + Math.min(delete, Math.min(insert, replace));
            }
        }
        return cost[i][j];
    }
}
