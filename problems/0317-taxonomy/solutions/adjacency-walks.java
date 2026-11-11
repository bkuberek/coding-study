import java.util.*;

/**
 * Every concept keeps the set of its parents and the set of its children. Questions about
 * ancestors, descendants, cycles and expansion are breadth-first walks over those sets, so nothing
 * recurses and a chain of 10^5 concepts is as safe as a flat list. Retired concepts keep their id
 * and their labels; a table of replacements sends them to a live concept, and every method that
 * takes an id first follows that table.
 */
public class Taxonomy {
    private final Map<String, String> label = new HashMap<>();
    private final Map<String, Set<String>> up = new HashMap<>();
    private final Map<String, Set<String>> down = new HashMap<>();
    private final Map<String, List<String>> alts = new HashMap<>();
    private final Map<String, Set<String>> index = new HashMap<>();
    private final Map<String, String> gone = new HashMap<>();
    private final Map<String, Set<String>> same = new HashMap<>();

    public Taxonomy() {
    }

    // Level 1
    public String addConcept(String concept, String label, List<String> parents) {
        if (this.label.containsKey(concept)) {
            return "duplicate";
        }
        if (parents.contains(concept)) {
            return "cycle";
        }
        for (String parent : parents) {
            if (!this.label.containsKey(parent)) {
                return "unknown-broader";
            }
        }
        Set<String> resolved = new HashSet<>();
        for (String parent : parents) {
            resolved.add(follow(parent));
        }
        for (String parent : resolved) {
            if (!scheme(parent).equals(scheme(concept))) {
                return "cross-scheme";
            }
        }
        this.label.put(concept, label);
        up.put(concept, resolved);
        down.put(concept, new HashSet<>());
        alts.put(concept, new ArrayList<>());
        same.put(concept, new HashSet<>());
        for (String parent : resolved) {
            down.get(parent).add(concept);
        }
        indexLabel(concept, label);
        return "ok";
    }

    public String addBroader(String narrower, String broader) {
        String child = follow(narrower);
        String parent = follow(broader);
        if (!label.containsKey(child) || !label.containsKey(parent)) {
            return "unknown-concept";
        }
        if (!scheme(child).equals(scheme(parent))) {
            return "cross-scheme";
        }
        if (child.equals(parent) || reach(parent, up).contains(child)) {
            return "cycle";
        }
        up.get(child).add(parent);
        down.get(parent).add(child);
        return "ok";
    }

    public String prefLabel(String concept) {
        return label.getOrDefault(follow(concept), "");
    }

    public List<String> broader(String concept) {
        return sorted(up.getOrDefault(follow(concept), Set.of()));
    }

    public List<String> narrower(String concept) {
        return sorted(down.getOrDefault(follow(concept), Set.of()));
    }

    public List<String> ancestors(String concept) {
        return nearestFirst(follow(concept), up);
    }

    public List<String> descendants(String concept) {
        return nearestFirst(follow(concept), down);
    }

    public List<String> roots() {
        List<String> found = new ArrayList<>();
        for (Map.Entry<String, Set<String>> entry : up.entrySet()) {
            if (!gone.containsKey(entry.getKey()) && entry.getValue().isEmpty()) {
                found.add(entry.getKey());
            }
        }
        Collections.sort(found);
        return found;
    }

    // Level 2
    public List<String> lowestCommonAncestors(String first, String second) {
        String a = follow(first);
        String b = follow(second);
        if (!label.containsKey(a) || !label.containsKey(b)) {
            return new ArrayList<>();
        }
        Set<String> common = reach(a, up);
        common.retainAll(reach(b, up));
        List<String> lowest = new ArrayList<>();
        for (String concept : common) {
            boolean covered = false;
            for (String kid : down.get(concept)) {
                if (common.contains(kid)) {
                    covered = true;
                    break;
                }
            }
            if (!covered) {
                lowest.add(concept);
            }
        }
        Collections.sort(lowest);
        return lowest;
    }

    // Level 3
    public String addAltLabel(String concept, String label) {
        String id = follow(concept);
        if (!this.label.containsKey(id)) {
            return "unknown-concept";
        }
        String key = normalize(label);
        if (key.isEmpty()) {
            return "empty-label";
        }
        if (normalize(this.label.get(id)).equals(key)) {
            return "duplicate";
        }
        for (String text : alts.get(id)) {
            if (normalize(text).equals(key)) {
                return "duplicate";
            }
        }
        alts.get(id).add(label);
        indexLabel(id, label);
        return "ok";
    }

    public List<String> altLabels(String concept) {
        return new ArrayList<>(alts.getOrDefault(follow(concept), List.of()));
    }

    public List<String> findByLabel(String label) {
        return sorted(matching(label));
    }

    public List<String> expand(List<String> labels) {
        Set<String> seen = new HashSet<>();
        List<String> queue = new ArrayList<>();
        for (String label : labels) {
            for (String concept : matching(label)) {
                if (seen.add(concept)) {
                    queue.add(concept);
                }
            }
        }
        for (int next = 0; next < queue.size(); next++) {
            for (String kid : down.get(queue.get(next))) {
                if (seen.add(kid)) {
                    queue.add(kid);
                }
            }
        }
        return sorted(seen);
    }

    // Level 4
    public String rename(String concept, String label) {
        String id = follow(concept);
        if (!this.label.containsKey(id)) {
            return "unknown-concept";
        }
        String old = this.label.get(id);
        String key = normalize(label);
        List<String> kept = new ArrayList<>();
        for (String text : alts.get(id)) {
            if (!normalize(text).equals(key)) {
                kept.add(text);
            }
        }
        String oldKey = normalize(old);
        if (!oldKey.isEmpty() && !oldKey.equals(key)) {
            kept.add(old);
        }
        alts.put(id, kept);
        this.label.put(id, label);
        indexLabel(id, label);
        return "ok";
    }

    public String removeBroader(String narrower, String broader) {
        String child = follow(narrower);
        String parent = follow(broader);
        if (!label.containsKey(child) || !label.containsKey(parent)) {
            return "unknown-concept";
        }
        if (!up.get(child).contains(parent)) {
            return "no-link";
        }
        up.get(child).remove(parent);
        down.get(parent).remove(child);
        return "ok";
    }

    public String deprecate(String concept, String replacement) {
        if (!label.containsKey(concept) || !label.containsKey(replacement)) {
            return "unknown-concept";
        }
        if (gone.containsKey(concept)) {
            return "deprecated";
        }
        String target = follow(replacement);
        if (target.equals(concept)) {
            return "same-concept";
        }
        if (!scheme(target).equals(scheme(concept))) {
            return "cross-scheme";
        }
        if (!down.get(concept).isEmpty()) {
            return "has-narrower";
        }
        for (String parent : up.get(concept)) {
            down.get(parent).remove(concept);
        }
        up.put(concept, new HashSet<>());
        for (String partner : same.get(concept)) {
            same.get(partner).remove(concept);
            same.get(partner).add(target);
            same.get(target).add(partner);
        }
        same.put(concept, new HashSet<>());
        gone.put(concept, target);
        return "ok";
    }

    public String resolve(String concept) {
        String id = follow(concept);
        return label.containsKey(id) ? id : "";
    }

    public String addExactMatch(String first, String second) {
        String a = follow(first);
        String b = follow(second);
        if (!label.containsKey(a) || !label.containsKey(b)) {
            return "unknown-concept";
        }
        if (scheme(a).equals(scheme(b))) {
            return "same-scheme";
        }
        same.get(a).add(b);
        same.get(b).add(a);
        return "ok";
    }

    public List<String> translate(List<String> concepts, String scheme) {
        Set<String> found = new HashSet<>();
        for (String concept : known(concepts)) {
            found.addAll(targets(concept, scheme));
        }
        return sorted(found);
    }

    public List<String> unmapped(List<String> concepts, String scheme) {
        List<String> found = new ArrayList<>();
        for (String concept : known(concepts)) {
            if (targets(concept, scheme).isEmpty()) {
                found.add(concept);
            }
        }
        return found;
    }

    // Helpers
    private static String scheme(String concept) {
        int colon = concept.indexOf(':');
        return colon < 0 ? "" : concept.substring(0, colon);
    }

    // Trim the spaces at both ends, turn each run of spaces into one, lower-case A to Z.
    private static String normalize(String label) {
        StringBuilder out = new StringBuilder();
        for (String part : label.split(" ")) {
            if (!part.isEmpty()) {
                if (out.length() > 0) {
                    out.append(' ');
                }
                out.append(part);
            }
        }
        return out.toString().toLowerCase(Locale.ROOT);
    }

    private static List<String> sorted(Collection<String> items) {
        List<String> list = new ArrayList<>(items);
        Collections.sort(list);
        return list;
    }

    private String follow(String concept) {
        String current = concept;
        while (gone.containsKey(current)) {
            current = gone.get(current);
        }
        if (!current.equals(concept)) {
            gone.put(concept, current);
        }
        return current;
    }

    private List<String> known(List<String> concepts) {
        Set<String> resolved = new HashSet<>();
        for (String concept : concepts) {
            String id = follow(concept);
            if (label.containsKey(id)) {
                resolved.add(id);
            }
        }
        return sorted(resolved);
    }

    private Set<String> targets(String concept, String scheme) {
        Set<String> found = new HashSet<>();
        if (scheme(concept).equals(scheme)) {
            found.add(concept);
            return found;
        }
        for (String partner : same.get(concept)) {
            if (scheme(partner).equals(scheme)) {
                found.add(partner);
            }
        }
        return found;
    }

    private void indexLabel(String concept, String label) {
        String key = normalize(label);
        if (!key.isEmpty()) {
            index.computeIfAbsent(key, k -> new HashSet<>()).add(concept);
        }
    }

    private Set<String> matching(String label) {
        Set<String> found = new HashSet<>();
        String key = normalize(label);
        if (key.isEmpty()) {
            return found;
        }
        for (String concept : new ArrayList<>(index.getOrDefault(key, Set.of()))) {
            found.add(follow(concept));
        }
        return found;
    }

    /** The concept itself and everything above (or below) it. */
    private static Set<String> reach(String start, Map<String, Set<String>> edges) {
        Set<String> seen = new HashSet<>();
        seen.add(start);
        List<String> queue = new ArrayList<>();
        queue.add(start);
        for (int next = 0; next < queue.size(); next++) {
            for (String neighbour : edges.get(queue.get(next))) {
                if (seen.add(neighbour)) {
                    queue.add(neighbour);
                }
            }
        }
        return seen;
    }

    private static List<String> nearestFirst(String start, Map<String, Set<String>> edges) {
        List<String> found = new ArrayList<>();
        if (!edges.containsKey(start)) {
            return found;
        }
        Set<String> seen = new HashSet<>();
        seen.add(start);
        List<String> level = List.of(start);
        while (!level.isEmpty()) {
            Set<String> following = new HashSet<>();
            for (String current : level) {
                for (String neighbour : edges.get(current)) {
                    if (!seen.contains(neighbour)) {
                        following.add(neighbour);
                    }
                }
            }
            seen.addAll(following);
            level = sorted(following);
            found.addAll(level);
        }
        return found;
    }
}
