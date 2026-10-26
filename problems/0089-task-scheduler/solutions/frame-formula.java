public class Solution {
    public int leastInterval(char[] tasks, int cooldown) {
        int[] counts = new int[26];
        for (char task : tasks) {
            counts[task - 'A']++;
        }
        int top = 0;
        int tied = 0;
        for (int count : counts) {
            if (count > top) {
                top = count;
                tied = 1;
            } else if (count == top) {
                tied++;
            }
        }
        // top - 1 full frames of cooldown + 1 slots, then one last partial frame holding the
        // tied most frequent tasks. With enough other tasks, no slot idles.
        return Math.max(tasks.length, (top - 1) * (cooldown + 1) + tied);
    }
}
