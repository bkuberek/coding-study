import java.util.*;

public class Solution {
    private static final String START = "0000";

    public int openLock(String[] deadends, String target) {
        Set<String> blocked = new HashSet<>(Arrays.asList(deadends));
        if (blocked.contains(START)) {
            return -1;
        }
        if (target.equals(START)) {
            return 0;
        }
        // Two frontiers grow toward each other; moves counts the levels expanded so far.
        Set<String> near = new HashSet<>(List.of(START));
        Set<String> far = new HashSet<>(List.of(target));
        Set<String> seen = new HashSet<>(List.of(START, target));
        int moves = 0;
        while (!near.isEmpty() && !far.isEmpty()) {
            if (near.size() > far.size()) {
                // Always expand the smaller frontier.
                Set<String> swap = near;
                near = far;
                far = swap;
            }
            moves++;
            Set<String> next = new HashSet<>();
            for (String setting : near) {
                for (String following : turns(setting)) {
                    if (far.contains(following)) {
                        return moves;
                    }
                    if (!blocked.contains(following) && seen.add(following)) {
                        next.add(following);
                    }
                }
            }
            near = next;
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
