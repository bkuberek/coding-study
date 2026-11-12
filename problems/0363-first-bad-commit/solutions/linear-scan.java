public class Solution {
    private static final int GOOD = 0;
    private static final int BAD = 1;

    public int[] firstBadCommit(int[] statuses) {
        int lastGood = -1;
        for (int position = 0; position < statuses.length; position++) {
            if (statuses[position] == GOOD) {
                lastGood = position;
            } else if (statuses[position] == BAD) {
                return new int[] {lastGood + 1, position};
            }
        }
        throw new IllegalArgumentException("the history has no bad commit");
    }
}
