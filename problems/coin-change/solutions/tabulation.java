import java.util.*;

public class Solution {
    public int coinChange(int[] coins, int amount) {
        // fewest[x] is the fewest coins that pay x exactly; amount + 1 means "cannot be paid".
        int unreachable = amount + 1;
        int[] fewest = new int[amount + 1];
        Arrays.fill(fewest, unreachable);
        fewest[0] = 0;
        for (int x = 1; x <= amount; x++) {
            for (int coin : coins) {
                if (coin <= x && fewest[x - coin] + 1 < fewest[x]) {
                    fewest[x] = fewest[x - coin] + 1;
                }
            }
        }
        return fewest[amount] == unreachable ? -1 : fewest[amount];
    }
}
