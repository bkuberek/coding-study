import java.util.*;
import java.util.regex.Pattern;

/**
 * Layers are kept as given and merged on demand, oldest first, with the rules of RFC 7396. Every
 * node of the merged tree remembers the layer that set it. A template is parsed in one
 * left-to-right pass into a tree of text, substitutions, conditionals and loops, and rendered with
 * a stack of loop bindings that shadow the values.
 */
public class ValuesRenderer {
    private static final Pattern KEY = Pattern.compile("[A-Za-z_][A-Za-z0-9_]*");
    private static final Pattern INDEX = Pattern.compile("0|[1-9][0-9]*");
    private static final String SEGMENT = "(?:[A-Za-z_][A-Za-z0-9_]*|0|[1-9][0-9]*)";
    private static final Pattern PATH = Pattern.compile(SEGMENT + "(?:\\." + SEGMENT + ")*");
    private static final Set<String> BLOCK_WORDS = Set.of("if", "else", "end", "for");
    private static final Set<String> RESERVED = Set.of("if", "else", "end", "for", "in");

    private static final class Node {
        final String kind;
        final String text;
        final String layer;
        final Map<String, Node> members = new HashMap<>();
        final List<Node> items = new ArrayList<>();

        Node(String kind, String text, String layer) {
            this.kind = kind;
            this.text = text;
            this.layer = layer;
        }

        Node copy(String newLayer) {
            Node twin = new Node(kind, text, newLayer);
            members.forEach((key, child) -> twin.members.put(key, child.copy(newLayer)));
            for (Node child : items) twin.items.add(child.copy(newLayer));
            return twin;
        }
    }

    private static final class TemplateError extends RuntimeException {
        final String code;
        final int position;
        final String detail;

        TemplateError(String code, int position, String detail) {
            super(code);
            this.code = code;
            this.position = position;
            this.detail = detail;
        }

        TemplateError(String code, int position) {
            this(code, position, "");
        }
    }

    private record Token(String kind, String value) {}

    /** A classified tag: kind is text, out, if, else, end or for. */
    private record Tag(String kind, String text, String path, String fallback, List<String> names) {}

    private record Segment(String text, Tag tag, int at, boolean trimLeft, boolean trimRight) {}

    /** A part of a parsed template: text, out, if or for. */
    private static final class Part {
        final String kind;
        final String text;
        final String path;
        final String fallback;
        final List<String> names;
        final int at;
        final List<Part> first = new ArrayList<>();
        final List<Part> second = new ArrayList<>();

        Part(String kind, String text, String path, String fallback, List<String> names, int at) {
            this.kind = kind;
            this.text = text;
            this.path = path;
            this.fallback = fallback;
            this.names = names;
            this.at = at;
        }
    }

    private record Binding(String name, Node node) {}

    private final LinkedHashMap<String, Node> layers = new LinkedHashMap<>();
    private Node schema = new Node("object", "", "");

    public ValuesRenderer() {}

    // Level 1
    public boolean setLayer(String name, List<List<String>> rows) {
        boolean isNew = !layers.containsKey(name);
        layers.put(name, decode(rows));
        return isNew;
    }

    public List<List<String>> merged() {
        List<List<String>> rows = new ArrayList<>();
        walk(merge(), "", (pointer, node) -> rows.add(List.of(pointer, node.kind, node.text)));
        return rows;
    }

    // Level 2 and 3
    public List<String> render(String template) {
        Node values = merge();
        List<List<String>> errors = errors(values);
        if (!errors.isEmpty()) return List.of("error", "invalid_values", "", String.valueOf(errors.size()));
        try {
            StringBuilder out = new StringBuilder();
            emit(parse(template), values, new ArrayList<>(), out);
            return List.of("ok", out.toString());
        } catch (TemplateError error) {
            return List.of("error", error.code, lineAndColumn(template, error.position), error.detail);
        }
    }

    // Level 4
    public void setSchema(List<List<String>> rows) {
        schema = decode(rows);
    }

    public List<List<String>> validate() {
        return errors(merge());
    }

    public List<List<String>> provenance() {
        List<List<String>> rows = new ArrayList<>();
        walk(merge(), "", (pointer, node) -> rows.add(List.of(pointer, node.layer)));
        return rows;
    }

    // Merging
    private Node merge() {
        Node root = new Node("object", "", "");
        layers.forEach((name, layer) -> mergeInto(root, layer, name));
        return root;
    }

    private static Node decode(List<List<String>> rows) {
        Node root = new Node("object", "", "");
        for (List<String> row : rows) {
            String[] segments = row.get(0).substring(1).split("/", -1);
            Node parent = root;
            for (int i = 0; i < segments.length - 1; i++) {
                parent = parent.kind.equals("object")
                        ? parent.members.get(segments[i])
                        : parent.items.get(Integer.parseInt(segments[i]));
            }
            Node node = new Node(row.get(1), row.get(2), "");
            if (parent.kind.equals("object")) parent.members.put(segments[segments.length - 1], node);
            else parent.items.add(node);
        }
        return root;
    }

    private interface Visitor {
        void visit(String pointer, Node node);
    }

    private static void walk(Node node, String pointer, Visitor visitor) {
        if (node.kind.equals("object")) {
            for (String key : new TreeSet<>(node.members.keySet())) {
                Node child = node.members.get(key);
                visitor.visit(pointer + "/" + key, child);
                walk(child, pointer + "/" + key, visitor);
            }
        } else if (node.kind.equals("array")) {
            for (int i = 0; i < node.items.size(); i++) {
                visitor.visit(pointer + "/" + i, node.items.get(i));
                walk(node.items.get(i), pointer + "/" + i, visitor);
            }
        }
    }

    private static void mergeInto(Node target, Node patch, String layer) {
        for (Map.Entry<String, Node> entry : patch.members.entrySet()) {
            String key = entry.getKey();
            Node value = entry.getValue();
            if (value.kind.equals("null")) {
                target.members.remove(key);
            } else if (value.kind.equals("object")) {
                Node current = target.members.get(key);
                if (current == null || !current.kind.equals("object")) {
                    current = new Node("object", "", layer);
                    target.members.put(key, current);
                }
                mergeInto(current, value, layer);
            } else {
                target.members.put(key, value.copy(layer));
            }
        }
    }

    // Parsing
    private static boolean isWordChar(char c) {
        return Character.isLetterOrDigit(c) && c < 128 || c == '_' || c == '.';
    }

    private static List<Token> tokenize(String body, int position) {
        List<Token> tokens = new ArrayList<>();
        int i = 0;
        while (i < body.length()) {
            char c = body.charAt(i);
            if (c == ' ') {
                i++;
            } else if (c == '|' || c == ',') {
                tokens.add(new Token("punct", String.valueOf(c)));
                i++;
            } else if (c == '"') {
                StringBuilder text = new StringBuilder();
                i++;
                while (true) {
                    if (i >= body.length()) throw new TemplateError("bad_expression", position);
                    char d = body.charAt(i);
                    if (d == '"') break;
                    if (d == '\\') {
                        if (i + 1 >= body.length() || (body.charAt(i + 1) != '"' && body.charAt(i + 1) != '\\')) {
                            throw new TemplateError("bad_expression", position);
                        }
                        text.append(body.charAt(i + 1));
                        i += 2;
                    } else {
                        text.append(d);
                        i++;
                    }
                }
                tokens.add(new Token("string", text.toString()));
                i++;
            } else if (isWordChar(c)) {
                int start = i;
                while (i < body.length() && isWordChar(body.charAt(i))) i++;
                tokens.add(new Token("word", body.substring(start, i)));
            } else {
                throw new TemplateError("bad_expression", position);
            }
        }
        return tokens;
    }

    private static Tag classify(List<Token> tokens, int position) {
        List<String> kinds = tokens.stream().map(Token::kind).toList();
        List<String> words = tokens.stream().map(Token::value).toList();
        if (!tokens.isEmpty() && kinds.get(0).equals("word") && BLOCK_WORDS.contains(words.get(0))) {
            return classifyBlock(kinds, words, position);
        }
        if (kinds.equals(List.of("string"))) return new Tag("text", words.get(0), null, null, null);
        if (kinds.equals(List.of("word")) && isPath(words.get(0))) {
            return new Tag("out", null, words.get(0), null, null);
        }
        if (kinds.equals(List.of("word", "punct", "word", "string"))
                && isPath(words.get(0))
                && words.get(1).equals("|")
                && words.get(2).equals("default")) {
            return new Tag("out", null, words.get(0), words.get(3), null);
        }
        throw new TemplateError("bad_expression", position);
    }

    private static Tag classifyBlock(List<String> kinds, List<String> words, int position) {
        String head = words.get(0);
        if ((head.equals("else") || head.equals("end")) && words.size() == 1) {
            return new Tag(head, null, null, null, null);
        }
        if (head.equals("if") && kinds.equals(List.of("word", "word")) && isPath(words.get(1))) {
            return new Tag("if", null, words.get(1), null, null);
        }
        if (head.equals("for")) {
            List<String> names = List.of();
            if (kinds.equals(List.of("word", "word", "word", "word")) && words.get(2).equals("in")) {
                names = List.of(words.get(1));
            } else if (kinds.equals(List.of("word", "word", "punct", "word", "word", "word"))
                    && words.get(2).equals(",")
                    && words.get(4).equals("in")) {
                names = List.of(words.get(1), words.get(3));
            }
            boolean valid = names.stream().allMatch(n -> KEY.matcher(n).matches() && !RESERVED.contains(n));
            String path = words.get(words.size() - 1);
            if (!names.isEmpty() && valid && new HashSet<>(names).size() == names.size() && isPath(path)) {
                return new Tag("for", null, path, null, names);
            }
        }
        throw new TemplateError("bad_expression", position);
    }

    private static boolean isPath(String word) {
        return PATH.matcher(word).matches();
    }

    private static List<Part> parse(String template) {
        List<Segment> segments = new ArrayList<>();
        Deque<int[]> stack = new ArrayDeque<>(); // {kind: 0 if / 1 for, position, has else}
        int i = 0;
        while (true) {
            int start = template.indexOf("{{", i);
            if (start < 0) {
                segments.add(new Segment(template.substring(i), null, 0, false, false));
                break;
            }
            segments.add(new Segment(template.substring(i, start), null, 0, false, false));
            int end = template.indexOf("}}", start + 2);
            if (end < 0) throw new TemplateError("unclosed_tag", start);
            String body = template.substring(start + 2, end);
            boolean trimLeft = body.startsWith("-");
            if (trimLeft) body = body.substring(1);
            boolean trimRight = body.endsWith("-");
            if (trimRight) body = body.substring(0, body.length() - 1);
            Tag tag = classify(tokenize(strip(body), start), start);
            switch (tag.kind()) {
                case "if" -> stack.push(new int[] {0, start, 0});
                case "for" -> stack.push(new int[] {1, start, 0});
                case "else" -> {
                    int[] top = stack.peek();
                    if (top == null || top[0] != 0 || top[2] == 1) throw new TemplateError("unexpected_tag", start);
                    top[2] = 1;
                }
                case "end" -> {
                    if (stack.isEmpty()) throw new TemplateError("unexpected_tag", start);
                    stack.pop();
                }
                default -> {}
            }
            segments.add(new Segment(null, tag, start, trimLeft, trimRight));
            i = end + 2;
        }
        if (!stack.isEmpty()) throw new TemplateError("unclosed_block", stack.peek()[1]);
        for (int k = 0; k < segments.size(); k++) {
            Segment segment = segments.get(k);
            if (segment.tag() == null) continue;
            if (segment.trimLeft()) {
                String before = segments.get(k - 1).text().replaceAll("[ \\n]+$", "");
                segments.set(k - 1, new Segment(before, null, 0, false, false));
            }
            if (segment.trimRight()) {
                String after = segments.get(k + 1).text().replaceAll("^[ \\n]+", "");
                segments.set(k + 1, new Segment(after, null, 0, false, false));
            }
        }
        return build(segments);
    }

    private static String strip(String body) {
        int start = 0;
        int end = body.length();
        while (start < end && body.charAt(start) == ' ') start++;
        while (end > start && body.charAt(end - 1) == ' ') end--;
        return body.substring(start, end);
    }

    private static List<Part> build(List<Segment> segments) {
        List<Part> root = new ArrayList<>();
        Deque<Part> blocks = new ArrayDeque<>();
        Deque<List<Part>> outers = new ArrayDeque<>();
        List<Part> current = root;
        for (Segment segment : segments) {
            Tag tag = segment.tag();
            if (tag == null) {
                if (!segment.text().isEmpty()) current.add(new Part("text", segment.text(), null, null, null, 0));
                continue;
            }
            switch (tag.kind()) {
                case "if", "for" -> {
                    Part block = new Part(tag.kind(), null, tag.path(), null, tag.names(), segment.at());
                    current.add(block);
                    blocks.push(block);
                    outers.push(current);
                    current = block.first;
                }
                case "else" -> current = blocks.peek().second;
                case "end" -> {
                    blocks.pop();
                    current = outers.pop();
                }
                case "text" -> current.add(new Part("text", tag.text(), null, null, null, 0));
                default -> current.add(new Part("out", null, tag.path(), tag.fallback(), null, segment.at()));
            }
        }
        return root;
    }

    private static String lineAndColumn(String template, int position) {
        int line = 1;
        int lineStart = 0;
        for (int i = 0; i < position; i++) {
            if (template.charAt(i) == '\n') {
                line++;
                lineStart = i + 1;
            }
        }
        return line + ":" + (position - lineStart + 1);
    }

    // Rendering
    private static void emit(List<Part> parts, Node values, List<Binding> scope, StringBuilder out) {
        for (Part part : parts) {
            switch (part.kind) {
                case "text" -> out.append(part.text);
                case "out" -> {
                    Node found = lookup(part.path, values, scope);
                    if (found == null) {
                        if (part.fallback == null) throw new TemplateError("missing_value", part.at, part.path);
                        out.append(part.fallback);
                    } else if (found.kind.equals("object") || found.kind.equals("array")) {
                        throw new TemplateError("not_scalar", part.at, part.path);
                    } else {
                        out.append(found.text);
                    }
                }
                case "if" -> {
                    boolean taken = truthy(lookup(part.path, values, scope));
                    emit(taken ? part.first : part.second, values, scope, out);
                }
                default -> loop(part, values, scope, out);
            }
        }
    }

    private static void loop(Part part, Node values, List<Binding> scope, StringBuilder out) {
        Node found = lookup(part.path, values, scope);
        if (found == null) throw new TemplateError("missing_value", part.at, part.path);
        List<Node[]> pairs = new ArrayList<>();
        if (found.kind.equals("array")) {
            for (int i = 0; i < found.items.size(); i++) {
                pairs.add(new Node[] {new Node("number", String.valueOf(i), ""), found.items.get(i)});
            }
        } else if (found.kind.equals("object")) {
            for (String key : new TreeSet<>(found.members.keySet())) {
                pairs.add(new Node[] {new Node("string", key, ""), found.members.get(key)});
            }
        } else {
            throw new TemplateError("not_iterable", part.at, part.path);
        }
        for (Node[] pair : pairs) {
            List<Binding> inner = new ArrayList<>(scope);
            if (part.names.size() == 2) {
                inner.add(new Binding(part.names.get(0), pair[0]));
                inner.add(new Binding(part.names.get(1), pair[1]));
            } else {
                inner.add(new Binding(part.names.get(0), pair[1]));
            }
            emit(part.first, values, inner, out);
        }
    }

    private static Node lookup(String path, Node values, List<Binding> scope) {
        String[] segments = path.split("\\.", -1);
        Node current = values;
        int from = 0;
        for (int i = scope.size() - 1; i >= 0; i--) {
            if (scope.get(i).name().equals(segments[0])) {
                current = scope.get(i).node();
                from = 1;
                break;
            }
        }
        for (int i = from; i < segments.length; i++) {
            if (current == null) return null;
            String segment = segments[i];
            if (current.kind.equals("object")) {
                current = current.members.get(segment);
            } else if (current.kind.equals("array") && INDEX.matcher(segment).matches()
                    && segment.length() < 10 && Integer.parseInt(segment) < current.items.size()) {
                current = current.items.get(Integer.parseInt(segment));
            } else {
                return null;
            }
        }
        return current == null || current.kind.equals("null") ? null : current;
    }

    private static boolean truthy(Node node) {
        if (node == null) return false;
        return switch (node.kind) {
            case "boolean" -> node.text.equals("true");
            case "string" -> !node.text.isEmpty();
            case "number" -> !node.text.equals("0");
            case "object" -> !node.members.isEmpty();
            default -> !node.items.isEmpty();
        };
    }

    // Validation
    private List<List<String>> errors(Node values) {
        List<List<String>> errors = new ArrayList<>();
        check(values, schema, "", errors);
        errors.sort(Comparator.<List<String>, String>comparing(e -> e.get(0)).thenComparing(e -> e.get(1)));
        return errors;
    }

    private static boolean hasType(Node node, String name) {
        return node.kind.equals(name) || (name.equals("integer") && node.kind.equals("number"));
    }

    private static boolean isListed(Node node, Node options) {
        if (node.kind.equals("object") || node.kind.equals("array")) return false;
        for (Node option : options.items) {
            if (option.kind.equals(node.kind) && option.text.equals(node.text)) return true;
        }
        return false;
    }

    private static void check(Node node, Node schema, String pointer, List<List<String>> errors) {
        Map<String, Node> keywords = schema.members;
        Node type = keywords.get("type");
        if (type != null && !hasType(node, type.text)) errors.add(List.of(pointer, "type", node.layer));
        Node options = keywords.get("enum");
        if (options != null && !isListed(node, options)) errors.add(List.of(pointer, "enum", node.layer));
        if (node.kind.equals("number")) {
            long value = Long.parseLong(node.text);
            Node minimum = keywords.get("minimum");
            if (minimum != null && value < Long.parseLong(minimum.text)) {
                errors.add(List.of(pointer, "minimum", node.layer));
            }
            Node maximum = keywords.get("maximum");
            if (maximum != null && value > Long.parseLong(maximum.text)) {
                errors.add(List.of(pointer, "maximum", node.layer));
            }
        }
        if (node.kind.equals("object")) {
            Node propertiesNode = keywords.get("properties");
            Map<String, Node> properties = propertiesNode == null ? Map.of() : propertiesNode.members;
            Node required = keywords.get("required");
            if (required != null) {
                for (Node key : required.items) {
                    if (!node.members.containsKey(key.text)) {
                        errors.add(List.of(pointer + "/" + key.text, "required", ""));
                    }
                }
            }
            Node additional = keywords.get("additionalProperties");
            boolean closed = additional != null && additional.text.equals("false");
            for (Map.Entry<String, Node> entry : node.members.entrySet()) {
                String key = entry.getKey();
                Node sub = properties.get(key);
                if (sub != null) {
                    check(entry.getValue(), sub, pointer + "/" + key, errors);
                } else if (closed) {
                    errors.add(List.of(pointer + "/" + key, "additionalProperties", entry.getValue().layer));
                }
            }
        }
        Node items = keywords.get("items");
        if (node.kind.equals("array") && items != null) {
            for (int i = 0; i < node.items.size(); i++) check(node.items.get(i), items, pointer + "/" + i, errors);
        }
    }
}
