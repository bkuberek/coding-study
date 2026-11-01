import java.util.Arrays;
import java.util.stream.Gatherers;

public class Solution {
    public int[] pairSums(int[] nums) {
        return Arrays.stream(nums)
                .boxed()
                .gather(Gatherers.windowSliding(2))
                .filter(window -> window.size() == 2)
                .mapToInt(window -> window.get(0) + window.get(1))
                .toArray();
    }
}
