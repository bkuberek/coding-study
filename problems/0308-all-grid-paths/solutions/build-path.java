import java.util.*;

public class Solution {
    public List<String> allGridPaths(int n) {
        List<String> paths = new ArrayList<>();
        extend(new StringBuilder(2 * (n - 1)), 0, 0, n - 1, paths);
        return paths;
    }

    private void extend(StringBuilder moves, int downs, int rights, int last, List<String> paths) {
        if (downs == last && rights == last) {
            paths.add(moves.toString());
            return;
        }
        // D is tried before R, so the paths come out in lexicographic order.
        if (downs < last) {
            moves.append('D');
            extend(moves, downs + 1, rights, last, paths);
            moves.deleteCharAt(moves.length() - 1);
        }
        if (rights < last) {
            moves.append('R');
            extend(moves, downs, rights + 1, last, paths);
            moves.deleteCharAt(moves.length() - 1);
        }
    }
}
