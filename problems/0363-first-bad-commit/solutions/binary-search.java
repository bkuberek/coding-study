public class Solution {
    private static final int BAD = 1;
    private static final int SKIP = 2;

    public int[] firstBadCommit(int[] statuses) {
        int firstBad = findFirstBad(statuses);
        int lastGood = findLastGoodBefore(statuses, firstBad);
        return new int[] {lastGood + 1, firstBad};
    }

    private int findFirstBad(int[] statuses) {
        // Some commit is bad, so the first bad commit is somewhere in [low, high].
        int low = 0;
        int high = statuses.length - 1;
        while (low < high) {
            int middle = (low + high) >>> 1;
            int probe = middle;
            while (probe >= low && statuses[probe] == SKIP) {
                probe--;
            }
            if (probe >= low && statuses[probe] == BAD) {
                high = probe;
            } else {
                low = middle + 1;
            }
        }
        return low;
    }

    private int findLastGoodBefore(int[] statuses, int firstBad) {
        // Before the first bad commit every commit that was tested is good. The last good one is
        // somewhere in [low, high], where -1 stands for "none".
        int low = -1;
        int high = firstBad - 1;
        while (low < high) {
            int middle = (low + high + 1) >> 1;
            int probe = middle;
            while (probe <= high && statuses[probe] == SKIP) {
                probe++;
            }
            if (probe <= high) {
                low = probe;
            } else {
                high = middle - 1;
            }
        }
        return low;
    }
}
