import java.util.*;

public class Solution {
    public List<String> allGridPaths(int n) {
        int steps = 2 * (n - 1);
        List<String> paths = new ArrayList<>();
        // Counting up from 0 reads the bits from the most significant one as the first move,
        // with 0 for D and 1 for R, so the sequences come out in lexicographic order.
        for (int pattern = 0; pattern < (1 << steps); pattern++) {
            StringBuilder moves = new StringBuilder(steps);
            int rights = 0;
            for (int step = 0; step < steps; step++) {
                int isRight = (pattern >> (steps - 1 - step)) & 1;
                moves.append(isRight == 1 ? 'R' : 'D');
                rights += isRight;
            }
            if (rights == n - 1) {
                paths.add(moves.toString());
            }
        }
        return paths;
    }
}
