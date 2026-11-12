import java.time.LocalDate;
import java.util.*;

/**
 * Manifests are kept as trees by id, rules as data in the order they were added. A check expands
 * each rule's pointer pattern over each manifest and tests the concrete pointers; a service's port
 * rule looks up the workloads its selector picks. Exceptions, severities, modes and fixes are
 * applied on top of the same list of violations.
 */
public class PolicyChecker {
    private static final List<String> SEVERITIES = List.of("critical", "high", "medium", "low");

    private static final class Node {
        final String kind;
        final String text;
        final Map<String, Node> members = new HashMap<>();
        final List<Node> items = new ArrayList<>();

        Node(String kind, String text) {
            this.kind = kind;
            this.text = text;
        }
    }

    private static final class Rule {
        String check;
        String kind;
        String pointer;
        List<String> tags;
        String severity = "medium";
        String mode = "deny";
        String fix = "";
    }

    private record Key(String ruleId, String manifestId) {}

    private record Allowance(String reason, LocalDate expires) {}

    private record Violation(String manifestId, String ruleId, String pointer) {}

    private final Map<String, Node> manifests = new HashMap<>();
    private final LinkedHashMap<String, Rule> rules = new LinkedHashMap<>();
    private final Map<Key, Allowance> allowances = new HashMap<>();

    public PolicyChecker() {}

    // Level 1
    public boolean addManifest(List<List<String>> rows) {
        Node root = decode(rows);
        String id = textOf(root, "/kind") + "/" + textOf(root, "/name");
        return manifests.put(id, root) == null;
    }

    public boolean requireField(String ruleId, String kind, String pointer) {
        return define(ruleId, "field", kind, pointer, List.of());
    }

    public boolean forbidTags(String ruleId, String kind, String pointer, List<String> tags) {
        return define(ruleId, "tags", kind, pointer, tags);
    }

    public List<List<String>> check() {
        List<List<String>> rows = new ArrayList<>();
        for (Violation v : violations()) rows.add(List.of(v.manifestId(), v.ruleId(), v.pointer()));
        return rows;
    }

    // Level 2
    public boolean requirePortTargets(String ruleId) {
        return define(ruleId, "ports", "service", "", List.of());
    }

    // Level 3
    public boolean allow(String ruleId, String manifestId, String reason, LocalDate expires) {
        return allowances.put(new Key(ruleId, manifestId), new Allowance(reason, expires)) == null;
    }

    public List<List<String>> checkOn(LocalDate today) {
        List<List<String>> rows = new ArrayList<>();
        for (Violation v : violations()) {
            Allowance allowance = active(v.ruleId(), v.manifestId(), today);
            String outcome = allowance == null ? "violation" : "excepted";
            String note = allowance == null ? "" : allowance.reason();
            rows.add(List.of(v.manifestId(), v.ruleId(), v.pointer(), outcome, note));
        }
        List<Key> expired = new ArrayList<>();
        allowances.forEach((key, allowance) -> {
            if (today.isAfter(allowance.expires())) expired.add(key);
        });
        expired.sort(Comparator.comparing(Key::manifestId).thenComparing(Key::ruleId));
        for (Key key : expired) {
            String expires = allowances.get(key).expires().toString();
            rows.add(List.of(key.manifestId(), key.ruleId(), "", "expired", expires));
        }
        return rows;
    }

    // Level 4
    public boolean configure(String ruleId, String severity, String mode, String fix) {
        Rule rule = rules.get(ruleId);
        if (rule == null) return false;
        rule.severity = severity;
        rule.mode = mode;
        rule.fix = fix;
        return true;
    }

    public List<List<String>> findings(LocalDate today) {
        List<List<String>> rows = new ArrayList<>();
        for (Violation v : violations()) {
            if (active(v.ruleId(), v.manifestId(), today) != null) continue;
            Rule rule = rules.get(v.ruleId());
            String[] fix = fixFor(rule, manifests.get(v.manifestId()), v.pointer());
            rows.add(List.of(v.manifestId(), v.ruleId(), v.pointer(), rule.severity, rule.mode, fix[0], fix[1]));
        }
        rows.sort(Comparator.comparingInt(row -> SEVERITIES.indexOf(row.get(3))));
        return rows;
    }

    public List<List<String>> decide(LocalDate today) {
        TreeMap<String, int[]> counts = new TreeMap<>();
        for (String id : manifests.keySet()) counts.put(id, new int[2]);
        for (List<String> row : findings(today)) counts.get(row.get(0))[row.get(4).equals("deny") ? 0 : 1]++;
        List<List<String>> rows = new ArrayList<>();
        counts.forEach((id, count) -> rows.add(List.of(
                id, count[0] > 0 ? "reject" : "admit", String.valueOf(count[0]), String.valueOf(count[1]))));
        return rows;
    }

    // Rules
    private boolean define(String ruleId, String check, String kind, String pointer, List<String> tags) {
        Rule rule = rules.get(ruleId);
        boolean isNew = rule == null;
        if (isNew) {
            rule = new Rule();
            rules.put(ruleId, rule);
        }
        rule.check = check;
        rule.kind = kind;
        rule.pointer = pointer;
        rule.tags = List.copyOf(tags);
        return isNew;
    }

    private List<Violation> violations() {
        List<Violation> found = new ArrayList<>();
        for (String manifestId : new TreeSet<>(manifests.keySet())) {
            Node root = manifests.get(manifestId);
            String kind = textOf(root, "/kind");
            for (Map.Entry<String, Rule> entry : rules.entrySet()) {
                Rule rule = entry.getValue();
                if (!rule.kind.equals("*") && !rule.kind.equals(kind)) continue;
                for (String pointer : broken(rule, root)) found.add(new Violation(manifestId, entry.getKey(), pointer));
            }
        }
        return found;
    }

    private List<String> broken(Rule rule, Node root) {
        if (rule.check.equals("ports")) return unservedPorts(root);
        List<String> broken = new ArrayList<>();
        for (String pointer : expand(root, rule.pointer)) {
            Node node = resolve(root, pointer);
            if (rule.check.equals("field")) {
                if (node == null || node.kind.equals("null") || (node.kind.equals("string") && node.text.isEmpty())) {
                    broken.add(pointer);
                }
            } else if (node != null && node.kind.equals("string") && !node.text.contains("@")) {
                String tag = tagSplit(node.text)[1];
                if (tag == null || rule.tags.contains(tag)) broken.add(pointer);
            }
        }
        return broken;
    }

    private List<String> unservedPorts(Node service) {
        Node selector = resolve(service, "/selector");
        if (selector == null || !selector.kind.equals("object") || selector.members.isEmpty()) {
            return List.of("/selector");
        }
        List<Set<String>> served = new ArrayList<>();
        for (Node root : manifests.values()) {
            if (!"workload".equals(textOf(root, "/kind")) || !selects(selector, root)) continue;
            Set<String> names = new HashSet<>();
            for (String pointer : expand(root, "/containers/*/ports/*/name")) names.add(textOf(root, pointer));
            served.add(names);
        }
        if (served.isEmpty()) return List.of("/selector");
        List<String> broken = new ArrayList<>();
        for (String pointer : expand(service, "/ports/*")) {
            String target = textOf(service, pointer + "/target");
            if (target != null && served.stream().anyMatch(names -> !names.contains(target))) {
                broken.add(pointer + "/target");
            }
        }
        return broken;
    }

    private static boolean selects(Node selector, Node workload) {
        for (Map.Entry<String, Node> pair : selector.members.entrySet()) {
            Node value = pair.getValue();
            if (!value.kind.equals("string") || !value.text.equals(textOf(workload, "/labels/" + pair.getKey()))) {
                return false;
            }
        }
        return true;
    }

    private Allowance active(String ruleId, String manifestId, LocalDate today) {
        Allowance allowance = allowances.get(new Key(ruleId, manifestId));
        return allowance != null && !today.isAfter(allowance.expires()) ? allowance : null;
    }

    private static String[] fixFor(Rule rule, Node root, String pointer) {
        String[] none = {"", ""};
        if (rule.fix.isEmpty() || rule.check.equals("ports")) return none;
        Node node = resolve(root, pointer);
        if (rule.check.equals("tags")) return new String[] {"replace", tagSplit(node.text)[0] + ":" + rule.fix};
        if (node != null) return new String[] {"replace", rule.fix};
        Node parent = resolve(root, pointer.substring(0, pointer.lastIndexOf('/')));
        return parent != null && parent.kind.equals("object") ? new String[] {"add", rule.fix} : none;
    }

    // Documents
    private static Node decode(List<List<String>> rows) {
        Node root = new Node("object", "");
        for (List<String> row : rows) {
            String[] segments = row.get(0).substring(1).split("/", -1);
            Node parent = root;
            for (int i = 0; i < segments.length - 1; i++) {
                parent = parent.kind.equals("object")
                        ? parent.members.get(segments[i])
                        : parent.items.get(Integer.parseInt(segments[i]));
            }
            Node node = new Node(row.get(1), row.get(2));
            if (parent.kind.equals("object")) parent.members.put(segments[segments.length - 1], node);
            else parent.items.add(node);
        }
        return root;
    }

    private static Node resolve(Node root, String pointer) {
        Node node = root;
        if (pointer.isEmpty()) return node;
        for (String segment : pointer.substring(1).split("/", -1)) {
            if (node == null) return null;
            if (node.kind.equals("object")) {
                node = node.members.get(segment);
            } else if (node.kind.equals("array") && segment.matches("[0-9]{1,9}")
                    && Integer.parseInt(segment) < node.items.size()) {
                node = node.items.get(Integer.parseInt(segment));
            } else {
                return null;
            }
        }
        return node;
    }

    private static List<String> expand(Node root, String pattern) {
        List<String> pointers = List.of("");
        for (String segment : pattern.substring(1).split("/", -1)) {
            List<String> next = new ArrayList<>();
            for (String pointer : pointers) {
                if (!segment.equals("*")) {
                    next.add(pointer + "/" + segment);
                    continue;
                }
                Node node = resolve(root, pointer);
                if (node == null || !node.kind.equals("array")) continue;
                for (int i = 0; i < node.items.size(); i++) next.add(pointer + "/" + i);
            }
            pointers = next;
        }
        return pointers;
    }

    /** The repository and the tag of an image reference; the tag is null when there is none. */
    private static String[] tagSplit(String image) {
        int colon = image.lastIndexOf(':');
        if (colon > image.lastIndexOf('/')) return new String[] {image.substring(0, colon), image.substring(colon + 1)};
        return new String[] {image, null};
    }

    private static String textOf(Node root, String pointer) {
        Node node = resolve(root, pointer);
        return node != null && node.kind.equals("string") ? node.text : null;
    }
}
