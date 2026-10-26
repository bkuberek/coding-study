import java.util.*;

public class Solution {
    public List<String> generateParenthesis(int n) {
        List<String> result = new ArrayList<>();
        extend(new StringBuilder(2 * n), 0, 0, n, result);
        return result;
    }

    private void extend(StringBuilder brackets, int opened, int closed, int n, List<String> result) {
        if (closed == n) {
            result.add(brackets.toString());
            return;
        }
        if (opened < n) {
            brackets.append('(');
            extend(brackets, opened + 1, closed, n, result);
            brackets.deleteCharAt(brackets.length() - 1);
        }
        // A ')' is allowed only while it has an unmatched '(' to close.
        if (closed < opened) {
            brackets.append(')');
            extend(brackets, opened, closed + 1, n, result);
            brackets.deleteCharAt(brackets.length() - 1);
        }
    }
}
