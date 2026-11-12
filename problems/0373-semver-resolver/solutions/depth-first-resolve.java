import java.util.*;
import java.util.regex.Pattern;

/**
 * Versions are parsed once into numbers and identifiers; ranges are expanded into comparator sets.
 * Resolving is a depth-first search that picks the smallest open package name and tries its
 * versions from the highest down, undoing a choice when the rest cannot be resolved. Explaining a
 * failure reruns the search with constraints left out, one at a time.
 */
public class SemverResolver {
    private static final Pattern NUMBER = Pattern.compile("0|[1-9][0-9]*");
    private static final Pattern IDENTIFIER = Pattern.compile("[0-9A-Za-z-]+");
    private static final Pattern DIGITS = Pattern.compile("[0-9]+");
    private static final Set<String> WILDCARDS = Set.of("x", "X", "*");
    private static final List<String> OPERATORS = List.of(">=", "<=", ">", "<", "=", "^", "~");

    private record Version(int major, int minor, int patch, List<String> pre) {
        String text() {
            String core = major + "." + minor + "." + patch;
            return pre.isEmpty() ? core : core + "-" + String.join(".", pre);
        }
    }

    private record Comparison(String operator, Version bound) {}

    private record Dependency(String name, String text, List<List<Comparison>> sets, int edge) {}

    private record Release(String name, String text, Version version, List<Dependency> dependencies) {}

    private record Root(String name, String text, List<List<Comparison>> sets) {}

    private final Map<String, List<Release>> releases = new HashMap<>();
    private final List<Release> published = new ArrayList<>();
    private int edges = 0;

    public SemverResolver() {
    }

    // Level 1
    public boolean isValid(String version) {
        return parse(version) != null;
    }

    public int compare(String first, String second) {
        return order(parse(first), parse(second));
    }

    public List<String> sortVersions(List<String> versions) {
        List<String> valid = new ArrayList<>();
        for (String text : versions) {
            if (parse(text) != null) {
                valid.add(text);
            }
        }
        valid.sort((x, y) -> {
            int found = order(parse(x), parse(y));
            return found != 0 ? found : Integer.signum(x.compareTo(y));
        });
        return valid;
    }

    public String changeKind(String before, String after) {
        Version old = parse(before);
        Version now = parse(after);
        if (old == null || now == null) {
            return "invalid";
        }
        int found = order(now, old);
        if (found < 0) {
            return "downgrade";
        }
        if (found == 0) {
            return "none";
        }
        if (now.major() != old.major()) {
            return "major";
        }
        if (now.minor() != old.minor()) {
            return "minor";
        }
        if (now.patch() != old.patch()) {
            return "patch";
        }
        return "pre-release";
    }

    // Level 2
    public List<String> expandRange(String versionRange) {
        List<List<Comparison>> sets = expand(versionRange);
        List<String> lines = new ArrayList<>();
        if (sets == null) {
            return lines;
        }
        for (List<Comparison> comparators : sets) {
            StringJoiner line = new StringJoiner(" ");
            for (Comparison comparator : comparators) {
                line.add(comparator.operator() + comparator.bound().text());
            }
            lines.add(line.toString());
        }
        return lines;
    }

    public boolean satisfies(String version, String versionRange) {
        Version parsed = parse(version);
        List<List<Comparison>> sets = expand(versionRange);
        return parsed != null && sets != null && inRange(parsed, sets);
    }

    public String maxSatisfying(List<String> versions, String versionRange) {
        List<List<Comparison>> sets = expand(versionRange);
        if (sets == null) {
            return "";
        }
        Version bestVersion = null;
        String best = "";
        for (String text : versions) {
            Version parsed = parse(text);
            if (parsed == null || !inRange(parsed, sets)) {
                continue;
            }
            int found = bestVersion == null ? 1 : order(parsed, bestVersion);
            if (found > 0 || (found == 0 && text.compareTo(best) > 0)) {
                bestVersion = parsed;
                best = text;
            }
        }
        return best;
    }

    // Level 3
    public String publish(String name, String version, List<List<String>> dependencies) {
        Version parsed = parse(version);
        if (parsed == null) {
            return "invalid-version";
        }
        List<Release> list = releases.computeIfAbsent(name, key -> new ArrayList<>());
        for (Release release : list) {
            if (order(release.version(), parsed) == 0) {
                return "duplicate";
            }
        }
        Set<String> names = new HashSet<>();
        List<List<List<Comparison>>> expanded = new ArrayList<>();
        for (List<String> pair : dependencies) {
            List<List<Comparison>> sets = expand(pair.get(1));
            if (sets == null || !names.add(pair.get(0)) || pair.get(0).equals(name)) {
                return "invalid-dependency";
            }
            expanded.add(sets);
        }
        List<Dependency> own = new ArrayList<>();
        for (int i = 0; i < dependencies.size(); i++) {
            List<String> pair = dependencies.get(i);
            own.add(new Dependency(pair.get(0), pair.get(1), expanded.get(i), edges++));
        }
        Release release = new Release(name, version, parsed, own);
        list.add(release);
        list.sort((a, b) -> order(b.version(), a.version()));
        published.add(release);
        return "ok";
    }

    public List<String> candidates(String name, String versionRange) {
        List<List<Comparison>> sets = expand(versionRange);
        List<String> found = new ArrayList<>();
        if (sets == null) {
            return found;
        }
        for (Release release : releases.getOrDefault(name, List.of())) {
            if (inRange(release.version(), sets)) {
                found.add(release.text());
            }
        }
        return found;
    }

    public List<String> resolve(List<List<String>> requirements) {
        return result(search(roots(requirements), Set.of(), Set.of(), Map.of()));
    }

    // Level 4
    public List<String> explain(List<List<String>> requirements) {
        List<Root> roots = roots(requirements);
        if (search(roots, Set.of(), Set.of(), Map.of()) != null) {
            return new ArrayList<>();
        }
        Set<Integer> droppedRoots = new HashSet<>();
        Set<Integer> droppedEdges = new HashSet<>();
        List<String> kept = new ArrayList<>();
        for (int i = 0; i < roots.size(); i++) {
            droppedRoots.add(i);
            if (search(roots, droppedRoots, droppedEdges, Map.of()) != null) {
                droppedRoots.remove(i);
                kept.add("root requires " + roots.get(i).name() + " " + roots.get(i).text());
            }
        }
        for (Release release : published) {
            for (Dependency dependency : release.dependencies()) {
                droppedEdges.add(dependency.edge());
                if (search(roots, droppedRoots, droppedEdges, Map.of()) != null) {
                    droppedEdges.remove(dependency.edge());
                    kept.add(release.name() + "@" + release.text() + " requires " + dependency.name() + " "
                            + dependency.text());
                }
            }
        }
        return kept;
    }

    public List<String> lockedResolve(List<List<String>> requirements, List<String> lock) {
        return result(search(roots(requirements), Set.of(), Set.of(), lockOf(lock)));
    }

    public List<String> update(List<List<String>> requirements, List<String> lock, List<String> unlock) {
        Map<String, String> before = lockOf(lock);
        Map<String, String> preferred = new HashMap<>(before);
        preferred.keySet().removeAll(unlock);
        Map<String, Release> chosen = search(roots(requirements), Set.of(), Set.of(), preferred);
        if (chosen == null) {
            return new ArrayList<>(List.of("unsatisfiable"));
        }
        SortedSet<String> names = new TreeSet<>(before.keySet());
        names.addAll(chosen.keySet());
        List<String> changes = new ArrayList<>();
        for (String name : names) {
            String old = before.get(name);
            String now = chosen.containsKey(name) ? chosen.get(name).text() : null;
            if (old == null) {
                changes.add(name + ": added " + now);
            } else if (now == null) {
                changes.add(name + ": removed " + old);
            } else if (!old.equals(now)) {
                changes.add(name + ": " + old + " -> " + now + " (" + changeKind(old, now) + ")");
            }
        }
        return changes;
    }

    // Versions and ranges
    private static Version parse(String text) {
        int plus = text.indexOf('+');
        String rest = plus >= 0 ? text.substring(0, plus) : text;
        if (plus >= 0) {
            for (String part : text.substring(plus + 1).split("\\.", -1)) {
                if (!IDENTIFIER.matcher(part).matches()) {
                    return null;
                }
            }
        }
        int dash = rest.indexOf('-');
        String[] numbers = (dash >= 0 ? rest.substring(0, dash) : rest).split("\\.", -1);
        if (numbers.length != 3) {
            return null;
        }
        for (String number : numbers) {
            if (!NUMBER.matcher(number).matches()) {
                return null;
            }
        }
        List<String> pre = dash >= 0 ? List.of(rest.substring(dash + 1).split("\\.", -1)) : List.of();
        for (String part : pre) {
            if (!IDENTIFIER.matcher(part).matches()
                    || (DIGITS.matcher(part).matches() && !NUMBER.matcher(part).matches())) {
                return null;
            }
        }
        return new Version(Integer.parseInt(numbers[0]), Integer.parseInt(numbers[1]),
                Integer.parseInt(numbers[2]), pre);
    }

    private static int compareIdentifiers(String a, String b) {
        boolean aNumeric = DIGITS.matcher(a).matches();
        boolean bNumeric = DIGITS.matcher(b).matches();
        if (aNumeric && bNumeric) {
            return Integer.compare(Integer.parseInt(a), Integer.parseInt(b));
        }
        if (aNumeric != bNumeric) {
            return aNumeric ? -1 : 1;
        }
        return Integer.signum(a.compareTo(b));
    }

    private static int order(Version a, Version b) {
        if (a.major() != b.major()) {
            return Integer.compare(a.major(), b.major());
        }
        if (a.minor() != b.minor()) {
            return Integer.compare(a.minor(), b.minor());
        }
        if (a.patch() != b.patch()) {
            return Integer.compare(a.patch(), b.patch());
        }
        // A release (no pre-release) sorts after every pre-release of its core.
        if (a.pre().isEmpty() || b.pre().isEmpty()) {
            return Integer.compare(b.pre().size(), a.pre().size());
        }
        for (int i = 0; i < Math.min(a.pre().size(), b.pre().size()); i++) {
            int found = compareIdentifiers(a.pre().get(i), b.pre().get(i));
            if (found != 0) {
                return found;
            }
        }
        return Integer.compare(a.pre().size(), b.pre().size());
    }

    private static Comparison below(int major, int minor, int patch) {
        return new Comparison("<", new Version(major, minor, patch, List.of("0")));
    }

    private static Version floorOf(List<Integer> numbers) {
        int[] padded = new int[3];
        for (int i = 0; i < numbers.size(); i++) {
            padded[i] = numbers.get(i);
        }
        return new Version(padded[0], padded[1], padded[2], List.of());
    }

    /** The leading numbers of a pattern such as {@code 1}, {@code 1.x} or {@code 1.2.*}, or null. */
    private static List<Integer> partial(String pattern) {
        String[] parts = pattern.split("\\.", -1);
        if (parts.length > 3) {
            return null;
        }
        List<Integer> numbers = new ArrayList<>();
        for (int i = 0; i < parts.length; i++) {
            if (WILDCARDS.contains(parts[i])) {
                for (int j = i; j < parts.length; j++) {
                    if (!WILDCARDS.contains(parts[j])) {
                        return null;
                    }
                }
                return numbers;
            }
            if (!NUMBER.matcher(parts[i]).matches()) {
                return null;
            }
            numbers.add(Integer.parseInt(parts[i]));
        }
        return numbers.size() < 3 ? numbers : null;
    }

    private static List<Comparison> wildcardRange(List<Integer> numbers) {
        if (numbers.isEmpty()) {
            return List.of(new Comparison(">=", floorOf(numbers)));
        }
        if (numbers.size() == 1) {
            return List.of(new Comparison(">=", floorOf(numbers)), below(numbers.get(0) + 1, 0, 0));
        }
        return List.of(new Comparison(">=", floorOf(numbers)), below(numbers.get(0), numbers.get(1) + 1, 0));
    }

    private static Comparison caretUpper(List<Integer> numbers) {
        Version floor = floorOf(numbers);
        if (floor.major() > 0 || numbers.size() == 1) {
            return below(floor.major() + 1, 0, 0);
        }
        if (floor.minor() > 0 || numbers.size() == 2) {
            return below(0, floor.minor() + 1, 0);
        }
        return below(0, 0, floor.patch() + 1);
    }

    private static List<Comparison> expandTerm(String term) {
        String operator = "";
        for (String candidate : OPERATORS) {
            if (term.startsWith(candidate)) {
                operator = candidate;
                break;
            }
        }
        String pattern = term.substring(operator.length());
        Version full = parse(pattern);
        if (full != null) {
            switch (operator) {
                case "", "=" -> {
                    return List.of(new Comparison("=", full));
                }
                case "~" -> {
                    return List.of(new Comparison(">=", full), below(full.major(), full.minor() + 1, 0));
                }
                case "^" -> {
                    return List.of(new Comparison(">=", full),
                            caretUpper(List.of(full.major(), full.minor(), full.patch())));
                }
                default -> {
                    return List.of(new Comparison(operator, full));
                }
            }
        }
        List<Integer> numbers = partial(pattern);
        if (numbers == null || !List.of("", "=", "^", "~").contains(operator)) {
            return null;
        }
        if (operator.equals("^") && !numbers.isEmpty()) {
            return List.of(new Comparison(">=", floorOf(numbers)), caretUpper(numbers));
        }
        return wildcardRange(numbers);
    }

    private static List<List<Comparison>> expand(String text) {
        List<List<Comparison>> sets = new ArrayList<>();
        for (String piece : text.split("\\|\\|", -1)) {
            List<Comparison> comparators = new ArrayList<>();
            for (String term : piece.split(" ")) {
                if (term.isEmpty()) {
                    continue;
                }
                List<Comparison> expanded = expandTerm(term);
                if (expanded == null) {
                    return null;
                }
                comparators.addAll(expanded);
            }
            if (comparators.isEmpty()) {
                return null;
            }
            sets.add(comparators);
        }
        return sets;
    }

    private static boolean holds(Version version, Comparison comparator) {
        int found = order(version, comparator.bound());
        return switch (comparator.operator()) {
            case "=" -> found == 0;
            case ">" -> found > 0;
            case ">=" -> found >= 0;
            case "<" -> found < 0;
            default -> found <= 0;
        };
    }

    private static boolean inSet(Version version, List<Comparison> comparators) {
        for (Comparison comparator : comparators) {
            if (!holds(version, comparator)) {
                return false;
            }
        }
        if (version.pre().isEmpty()) {
            return true;
        }
        for (Comparison comparator : comparators) {
            Version bound = comparator.bound();
            if (!bound.pre().isEmpty() && bound.major() == version.major() && bound.minor() == version.minor()
                    && bound.patch() == version.patch()) {
                return true;
            }
        }
        return false;
    }

    private static boolean inRange(Version version, List<List<Comparison>> sets) {
        for (List<Comparison> comparators : sets) {
            if (inSet(version, comparators)) {
                return true;
            }
        }
        return false;
    }

    // The search
    private List<Root> roots(List<List<String>> requirements) {
        List<Root> roots = new ArrayList<>();
        for (List<String> pair : requirements) {
            roots.add(new Root(pair.get(0), pair.get(1), expand(pair.get(1))));
        }
        return roots;
    }

    private static Map<String, String> lockOf(List<String> lock) {
        Map<String, String> found = new HashMap<>();
        for (String entry : lock) {
            int at = entry.indexOf('@');
            found.put(entry.substring(0, at), entry.substring(at + 1));
        }
        return found;
    }

    private static List<String> result(Map<String, Release> chosen) {
        List<String> lines = new ArrayList<>();
        if (chosen == null) {
            return lines;
        }
        for (String name : new TreeSet<>(chosen.keySet())) {
            lines.add(name + "@" + chosen.get(name).text());
        }
        return lines;
    }

    /**
     * The chosen release of every needed package, or null when the constraints in force cannot all
     * hold.
     */
    private Map<String, Release> search(List<Root> roots, Set<Integer> droppedRoots, Set<Integer> droppedEdges,
            Map<String, String> preferred) {
        List<Root> rootRanges = new ArrayList<>();
        for (int i = 0; i < roots.size(); i++) {
            if (!droppedRoots.contains(i)) {
                rootRanges.add(roots.get(i));
            }
        }
        Map<String, Release> chosen = new HashMap<>();
        return solve(rootRanges, droppedEdges, preferred, chosen) ? new HashMap<>(chosen) : null;
    }

    private boolean solve(List<Root> rootRanges, Set<Integer> droppedEdges, Map<String, String> preferred,
            Map<String, Release> chosen) {
        SortedSet<String> open = new TreeSet<>();
        for (Root root : rootRanges) {
            open.add(root.name());
        }
        for (Release release : chosen.values()) {
            for (Dependency dependency : release.dependencies()) {
                if (!droppedEdges.contains(dependency.edge())) {
                    open.add(dependency.name());
                }
            }
        }
        open.removeAll(chosen.keySet());
        if (open.isEmpty()) {
            return true;
        }
        String name = open.first();
        List<List<List<Comparison>>> ranges = new ArrayList<>();
        for (Root root : rootRanges) {
            if (root.name().equals(name)) {
                ranges.add(root.sets());
            }
        }
        for (Release release : chosen.values()) {
            for (Dependency dependency : release.dependencies()) {
                if (!droppedEdges.contains(dependency.edge()) && dependency.name().equals(name)) {
                    ranges.add(dependency.sets());
                }
            }
        }
        List<Release> tries = new ArrayList<>();
        String wanted = preferred.get(name);
        for (Release release : releases.getOrDefault(name, List.of())) {
            if (release.text().equals(wanted)) {
                tries.add(0, release);
            } else {
                tries.add(release);
            }
        }
        for (Release release : tries) {
            if (!acceptable(release, ranges, droppedEdges, chosen)) {
                continue;
            }
            chosen.put(name, release);
            if (solve(rootRanges, droppedEdges, preferred, chosen)) {
                return true;
            }
            chosen.remove(name);
        }
        return false;
    }

    private static boolean acceptable(Release release, List<List<List<Comparison>>> ranges,
            Set<Integer> droppedEdges, Map<String, Release> chosen) {
        for (List<List<Comparison>> sets : ranges) {
            if (!inRange(release.version(), sets)) {
                return false;
            }
        }
        for (Dependency dependency : release.dependencies()) {
            Release other = chosen.get(dependency.name());
            if (!droppedEdges.contains(dependency.edge()) && other != null
                    && !inRange(other.version(), dependency.sets())) {
                return false;
            }
        }
        return true;
    }
}
