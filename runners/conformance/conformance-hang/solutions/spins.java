import java.util.*;

public class Solution {
    public int waitFor(int value) {
        while (value < 0) {
            Thread.onSpinWait();
        }
        return value;
    }
}
