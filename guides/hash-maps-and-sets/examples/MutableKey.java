import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

// Java lets a mutable object be a key. Changing it while it is stored changes its hashCode, so the
// map looks for it in the wrong bucket.
public class MutableKey {
    public static void main(String[] args) {
        List<String> route = new ArrayList<>(List.of("home", "office"));
        Map<List<String>, Integer> minutes = new HashMap<>();
        minutes.put(route, 25);
        System.out.println("before: get(route) = " + minutes.get(route));

        route.add("gym");  // the key changes while it is in the map
        System.out.println("after:  get(route) = " + minutes.get(route));
        System.out.println("after:  containsKey(route) = " + minutes.containsKey(route));
        System.out.println("after:  size() = " + minutes.size());
        boolean stillThere = false;
        for (List<String> key : minutes.keySet()) {
            stillThere |= key == route;
        }
        System.out.println("after:  the same object is still a key = " + stillThere);
    }
}
