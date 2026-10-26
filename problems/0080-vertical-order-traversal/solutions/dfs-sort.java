import cs.support.*;
import java.util.*;

public class Solution {
    public List<List<Integer>> verticalOrder(TreeNode root) {
        List<int[]> entries = new ArrayList<>(); // {column, row, value} in pre-order
        visit(root, 0, 0, entries);
        // List.sort is a stable merge sort, so pre-order (left to right) survives among ties.
        entries.sort(Comparator.<int[]>comparingInt(entry -> entry[0]).thenComparingInt(entry -> entry[1]));
        List<List<Integer>> columns = new ArrayList<>();
        for (int i = 0; i < entries.size(); i++) {
            if (i == 0 || entries.get(i)[0] != entries.get(i - 1)[0]) {
                columns.add(new ArrayList<>());
            }
            columns.get(columns.size() - 1).add(entries.get(i)[2]);
        }
        return columns;
    }

    private static void visit(TreeNode node, int column, int row, List<int[]> entries) {
        if (node == null) {
            return;
        }
        entries.add(new int[] {column, row, node.val});
        visit(node.left, column - 1, row + 1, entries);
        visit(node.right, column + 1, row + 1, entries);
    }
}
