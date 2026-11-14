import java.util.*;

public class Solution {
    private static final String START = "0000";

    public int openLock(String[] deadends, String target) {
        // Dead ends behave like settings that were already visited: the search never enters them.
        Set<String> seen = new HashSet<>(Arrays.asList(deadends));
        if (seen.contains(START)) {
            return -1;
        }
        seen.add(START);
        Queue<String> queue = new ArrayDeque<>();
        queue.add(START);
        for (int moves = 0; !queue.isEmpty(); moves++) {
            for (int i = queue.size(); i > 0; i--) {
                String setting = queue.poll();
                if (setting.equals(target)) {
                    return moves;
                }
                for (String following : turns(setting)) {
                    if (seen.add(following)) {
                        queue.add(following);
                    }
                }
            }
        }
        return -1;
    }

    /** The eight settings one move away: each wheel up or down by one, wrapping around. */
    private static List<String> turns(String setting) {
        List<String> result = new ArrayList<>(8);
        char[] wheels = setting.toCharArray();
        for (int wheel = 0; wheel < 4; wheel++) {
            char original = wheels[wheel];
            for (int turn : new int[] {1, 9}) {
                wheels[wheel] = (char) ('0' + (original - '0' + turn) % 10);
                result.add(new String(wheels));
            }
            wheels[wheel] = original;
        }
        return result;
    }
}
