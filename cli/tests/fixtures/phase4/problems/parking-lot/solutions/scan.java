import java.util.*;

public class ParkingLot {
    private final boolean[] occupied;
    private final Map<String, Integer> spotOf = new HashMap<>();

    public ParkingLot(int spots) {
        occupied = new boolean[spots];
    }

    public int park(String plate) {
        if (spotOf.containsKey(plate)) {
            return -1;
        }
        for (int spot = 0; spot < occupied.length; spot++) {
            if (!occupied[spot]) {
                occupied[spot] = true;
                spotOf.put(plate, spot);
                return spot;
            }
        }
        return -1;
    }

    public boolean leave(String plate) {
        Integer spot = spotOf.remove(plate);
        if (spot == null) {
            return false;
        }
        occupied[spot] = false;
        return true;
    }

    public int available() {
        return occupied.length - spotOf.size();
    }
}
