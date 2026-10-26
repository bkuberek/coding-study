import java.util.*;

public class Solution {
    public String decodeString(String s) {
        while (s.indexOf('[') >= 0) {
            // The first ']' closes an innermost group: the last '[' before it is its opener.
            int close = s.indexOf(']');
            int open = s.lastIndexOf('[', close);
            int start = open;
            while (start > 0 && Character.isDigit(s.charAt(start - 1))) {
                start--;
            }
            int count = Integer.parseInt(s, start, open, 10);
            s = s.substring(0, start) + s.substring(open + 1, close).repeat(count) + s.substring(close + 1);
        }
        return s;
    }
}
