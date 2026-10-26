public class Solution {
    public int totalFruit(int[] fruits) {
        int best = 0;
        for (int start = 0; start < fruits.length; start++) {
            int first = fruits[start];
            int second = -1;
            int end = start;
            while (end < fruits.length) {
                int fruit = fruits[end];
                if (fruit != first && fruit != second) {
                    if (second != -1) {
                        break;
                    }
                    second = fruit;
                }
                end++;
            }
            best = Math.max(best, end - start);
        }
        return best;
    }
}
