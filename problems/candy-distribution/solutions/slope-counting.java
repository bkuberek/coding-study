import java.util.*;

public class Solution {
    public int candy(int[] ratings) {
        int total = 1;
        int up = 0; // length of the current rising run: the latest child got up + 1 candies
        int down = 0; // length of the current falling run
        int peak = 0; // the rising run length at the top of the current peak
        for (int i = 1; i < ratings.length; i++) {
            if (ratings[i] > ratings[i - 1]) {
                up++;
                peak = up;
                down = 0;
                total += up + 1;
            } else if (ratings[i] == ratings[i - 1]) {
                up = 0;
                down = 0;
                peak = 0;
                total += 1;
            } else {
                up = 0;
                down++;
                // Every child on the falling run gets one more candy; the peak only needs one
                // more once the falling run is longer than the rising run that built it.
                total += down + (down > peak ? 1 : 0);
            }
        }
        return total;
    }
}
