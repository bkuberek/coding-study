import java.util.*;

public class Solution {
    public int leastInterval(char[] tasks, int cooldown) {
        int[] counts = new int[26];
        for (char task : tasks) {
            counts[task - 'A']++;
        }
        // Remaining counts of the tasks that may run now, largest first.
        PriorityQueue<Integer> ready = new PriorityQueue<>(Comparator.reverseOrder());
        for (int count : counts) {
            if (count > 0) {
                ready.offer(count);
            }
        }
        // Tasks that just ran, as {time they may run again, remaining count}, in time order.
        Deque<int[]> cooling = new ArrayDeque<>();
        int time = 0;
        while (!ready.isEmpty() || !cooling.isEmpty()) {
            if (!ready.isEmpty()) {
                int remaining = ready.poll() - 1;
                if (remaining > 0) {
                    cooling.addLast(new int[] {time + cooldown + 1, remaining});
                }
                time++;
            } else {
                time = cooling.peekFirst()[0]; // nothing can run: skip the idle stretch at once
            }
            while (!cooling.isEmpty() && cooling.peekFirst()[0] <= time) {
                ready.offer(cooling.pollFirst()[1]);
            }
        }
        return time;
    }
}
