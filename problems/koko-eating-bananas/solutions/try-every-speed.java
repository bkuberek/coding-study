public class Solution {
    public int minEatingSpeed(int[] piles, int h) {
        int speed = 1;
        while (hoursAt(piles, speed) > h) {
            speed++;
        }
        return speed;
    }

    private static long hoursAt(int[] piles, int speed) {
        long hours = 0;
        for (int pile : piles) {
            hours += (pile + (long) speed - 1) / speed;
        }
        return hours;
    }
}
