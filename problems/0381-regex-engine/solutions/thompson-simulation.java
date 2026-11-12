import java.util.*;

/**
 * A recursive-descent parser builds the syntax tree; Thompson's construction turns it into an
 * automaton with one state per character, class or operator; matching runs every live state in
 * step with the text, so it never backtracks. Compiled automata are cached by pattern.
 */
public class RegexEngine {
    private final Map<String, Automaton> automata = new HashMap<>();

    public RegexEngine() {
    }

    private Automaton automaton(String pattern) {
        return automata.computeIfAbsent(pattern, p -> new Automaton(new Parser(p).parse()));
    }

    // Level 1
    public String parse(String pattern) {
        try {
            return new Parser(pattern).parse().show();
        } catch (PatternError error) {
            return "error: " + error.code + " at " + error.position;
        }
    }

    // Level 2
    public List<String> nfa(String pattern) {
        Automaton automaton = automaton(pattern);
        List<String> lines = new ArrayList<>();
        for (int state = 0; state < automaton.size(); state++) {
            lines.add(automaton.line(state));
        }
        return lines;
    }

    // Level 3
    public boolean fullMatch(String pattern, String text) {
        return automaton(pattern).run(text).matched;
    }

    public int countSteps(String pattern, String text) {
        return automaton(pattern).run(text).steps;
    }

    // Level 4
    public int[] search(String pattern, String text) {
        return automaton(pattern).leftmostLongest(text);
    }

    static final class PatternError extends RuntimeException {
        final String code;
        final int position;

        PatternError(String code, int position) {
            super(code);
            this.code = code;
            this.position = position;
        }
    }

    /** A tree node: kind is lit, any, empty, class, cat, alt, star, plus or opt. */
    static final class Node {
        final String kind;
        final char ch;
        final boolean negated;
        final List<char[]> items;
        final List<Node> parts;

        Node(String kind, char ch, boolean negated, List<char[]> items, List<Node> parts) {
            this.kind = kind;
            this.ch = ch;
            this.negated = negated;
            this.items = items;
            this.parts = parts;
        }

        static Node leaf(String kind) {
            return new Node(kind, '\0', false, List.of(), List.of());
        }

        static Node literal(char ch) {
            return new Node("lit", ch, false, List.of(), List.of());
        }

        static Node of(String kind, List<Node> parts) {
            return new Node(kind, '\0', false, List.of(), parts);
        }

        String showClass() {
            StringJoiner joiner = new StringJoiner(",", negated ? "notclass(" : "class(", ")");
            for (char[] item : items) {
                joiner.add(item[0] == item[1] ? "'" + item[0] + "'" : "'" + item[0] + "'-'" + item[1] + "'");
            }
            return joiner.toString();
        }

        String show() {
            switch (kind) {
                case "lit":
                    return "'" + ch + "'";
                case "any":
                case "empty":
                    return kind;
                case "class":
                    return showClass();
                default:
                    StringJoiner joiner = new StringJoiner(",", kind + "(", ")");
                    for (Node part : parts) {
                        joiner.add(part.show());
                    }
                    return joiner.toString();
            }
        }

        boolean accepts(char c) {
            boolean inside = false;
            for (char[] item : items) {
                if (item[0] <= c && c <= item[1]) {
                    inside = true;
                }
            }
            return inside != negated;
        }
    }

    /** Recursive descent; a pattern has at most 100 characters, so the recursion stays shallow. */
    static final class Parser {
        private final String text;
        private int pos = 0;

        Parser(String text) {
            this.text = text;
        }

        private char peek() {
            return pos < text.length() ? text.charAt(pos) : '\0';
        }

        private boolean atEnd() {
            return pos >= text.length();
        }

        private static String repeat(char c) {
            switch (c) {
                case '*':
                    return "star";
                case '+':
                    return "plus";
                case '?':
                    return "opt";
                default:
                    return null;
            }
        }

        Node parse() {
            Node node = alternation();
            if (!atEnd()) {
                throw new PatternError("unmatched-paren", pos);
            }
            return node;
        }

        private Node alternation() {
            List<Node> branches = new ArrayList<>();
            branches.add(sequence());
            while (!atEnd() && peek() == '|') {
                pos++;
                branches.add(sequence());
            }
            return branches.size() == 1 ? branches.get(0) : Node.of("alt", branches);
        }

        private Node sequence() {
            List<Node> items = new ArrayList<>();
            while (!atEnd() && peek() != '|' && peek() != ')') {
                items.add(repetition());
            }
            if (items.isEmpty()) {
                return Node.leaf("empty");
            }
            return items.size() == 1 ? items.get(0) : Node.of("cat", items);
        }

        private Node repetition() {
            if (repeat(peek()) != null) {
                throw new PatternError("nothing-to-repeat", pos);
            }
            Node node = atom();
            while (!atEnd() && repeat(peek()) != null) {
                node = Node.of(repeat(peek()), List.of(node));
                pos++;
            }
            return node;
        }

        private Node atom() {
            int start = pos;
            char c = peek();
            pos++;
            if (c == '(') {
                Node inner = alternation();
                if (atEnd() || peek() != ')') {
                    throw new PatternError("unclosed-group", start);
                }
                pos++;
                return inner;
            }
            if (c == '.') {
                return Node.leaf("any");
            }
            if (c == '[') {
                return charClass(start);
            }
            return Node.literal(c);
        }

        private Node charClass(int start) {
            boolean negated = !atEnd() && peek() == '^';
            if (negated) {
                pos++;
            }
            List<char[]> items = new ArrayList<>();
            while (true) {
                if (atEnd()) {
                    throw new PatternError("unclosed-class", start);
                }
                if (peek() == ']') {
                    if (items.isEmpty()) {
                        throw new PatternError("empty-class", start);
                    }
                    pos++;
                    return new Node("class", '\0', negated, items, List.of());
                }
                int lowAt = pos;
                char low = text.charAt(lowAt);
                pos++;
                boolean isRange = !atEnd() && peek() == '-' && pos + 1 < text.length() && text.charAt(pos + 1) != ']';
                if (isRange) {
                    char high = text.charAt(pos + 1);
                    if (high < low) {
                        throw new PatternError("bad-range", lowAt);
                    }
                    pos += 2;
                    items.add(new char[] {low, high});
                } else {
                    items.add(new char[] {low, low});
                }
            }
        }
    }

    static final class Run {
        final boolean matched;
        final int steps;

        Run(boolean matched, int steps) {
            this.matched = matched;
            this.steps = steps;
        }
    }

    /** Parallel lists: the kind of each state, the node labelling a char or class state, its arrows. */
    static final class Automaton {
        private List<String> kind = new ArrayList<>();
        private List<Node> label = new ArrayList<>();
        private List<int[]> outs = new ArrayList<>();
        private int finalState;

        Automaton(Node root) {
            int[] start = new int[1];
            List<int[]> holes = fragment(root, start);
            int match = add("match", null, 0);
            patch(holes, match);
            renumber(start[0]);
        }

        int size() {
            return kind.size();
        }

        private int add(String k, Node node, int arrows) {
            kind.add(k);
            label.add(node);
            int[] arrowsOut = new int[arrows];
            Arrays.fill(arrowsOut, -1);
            outs.add(arrowsOut);
            return kind.size() - 1;
        }

        private void patch(List<int[]> holes, int target) {
            for (int[] hole : holes) {
                outs.get(hole[0])[hole[1]] = target;
            }
        }

        /** Builds the fragment of a node, stores its start in start[0] and returns its loose arrows. */
        private List<int[]> fragment(Node node, int[] start) {
            switch (node.kind) {
                case "lit":
                case "any":
                case "empty":
                case "class": {
                    int state = add(node.kind.equals("lit") ? "char" : node.kind, node, 1);
                    start[0] = state;
                    return new ArrayList<>(List.of(new int[] {state, 0}));
                }
                case "cat": {
                    List<int[]> holes = fragment(node.parts.get(0), start);
                    int first = start[0];
                    for (Node part : node.parts.subList(1, node.parts.size())) {
                        List<int[]> next = fragment(part, start);
                        patch(holes, start[0]);
                        holes = next;
                    }
                    start[0] = first;
                    return holes;
                }
                case "alt": {
                    int split = add("split", null, node.parts.size());
                    List<int[]> holes = new ArrayList<>();
                    for (int i = 0; i < node.parts.size(); i++) {
                        holes.addAll(fragment(node.parts.get(i), start));
                        outs.get(split)[i] = start[0];
                    }
                    start[0] = split;
                    return holes;
                }
                default: {
                    List<int[]> inner = fragment(node.parts.get(0), start);
                    int innerStart = start[0];
                    int split = add("split", null, 2);
                    outs.get(split)[0] = innerStart;
                    List<int[]> holes = new ArrayList<>();
                    if (node.kind.equals("opt")) {
                        holes.addAll(inner);
                    } else {
                        patch(inner, split);
                    }
                    holes.add(new int[] {split, 1});
                    start[0] = node.kind.equals("plus") ? innerStart : split;
                    return holes;
                }
            }
        }

        /** Breadth first from the start state: the start is 0, and each arrow's unseen target is next. */
        private void renumber(int start) {
            int[] number = new int[kind.size()];
            Arrays.fill(number, -1);
            List<Integer> order = new ArrayList<>();
            number[start] = 0;
            order.add(start);
            for (int i = 0; i < order.size(); i++) {
                for (int target : outs.get(order.get(i))) {
                    if (number[target] < 0) {
                        number[target] = order.size();
                        order.add(target);
                    }
                }
            }
            List<String> newKind = new ArrayList<>();
            List<Node> newLabel = new ArrayList<>();
            List<int[]> newOuts = new ArrayList<>();
            for (int state : order) {
                newKind.add(kind.get(state));
                newLabel.add(label.get(state));
                int[] old = outs.get(state);
                int[] renamed = new int[old.length];
                for (int j = 0; j < old.length; j++) {
                    renamed[j] = number[old[j]];
                }
                newOuts.add(renamed);
            }
            kind = newKind;
            label = newLabel;
            outs = newOuts;
            finalState = kind.indexOf("match");
        }

        String line(int state) {
            String k = kind.get(state);
            StringBuilder head = new StringBuilder().append(state).append(": ");
            if (k.equals("char")) {
                head.append("char '").append(label.get(state).ch).append('\'');
            } else if (k.equals("class")) {
                head.append(label.get(state).showClass());
            } else {
                head.append(k);
            }
            int[] arrows = outs.get(state);
            if (arrows.length > 0) {
                StringJoiner joiner = new StringJoiner(", ", " -> ", "");
                for (int target : arrows) {
                    joiner.add(Integer.toString(target));
                }
                head.append(joiner);
            }
            return head.toString();
        }

        private boolean accepts(int state, char c) {
            switch (kind.get(state)) {
                case "char":
                    return label.get(state).ch == c;
                case "any":
                    return true;
                case "class":
                    return label.get(state).accepts(c);
                default:
                    return false;
            }
        }

        private boolean silent(int state) {
            String k = kind.get(state);
            return k.equals("split") || k.equals("empty");
        }

        /** Every state reachable from the sources through split and empty arrows, sources included. */
        List<Integer> closure(List<Integer> sources) {
            boolean[] seen = new boolean[kind.size()];
            List<Integer> reached = new ArrayList<>();
            Deque<Integer> stack = new ArrayDeque<>();
            for (int i = sources.size() - 1; i >= 0; i--) {
                stack.push(sources.get(i));
            }
            while (!stack.isEmpty()) {
                int state = stack.pop();
                if (seen[state]) {
                    continue;
                }
                seen[state] = true;
                reached.add(state);
                if (silent(state)) {
                    int[] arrows = outs.get(state);
                    for (int i = arrows.length - 1; i >= 0; i--) {
                        stack.push(arrows[i]);
                    }
                }
            }
            return reached;
        }

        private List<Integer> advance(List<Integer> current, char c) {
            List<Integer> targets = new ArrayList<>();
            for (int state : current) {
                if (accepts(state, c)) {
                    targets.add(outs.get(state)[0]);
                }
            }
            return closure(targets);
        }

        Run run(String text) {
            List<Integer> current = closure(List.of(0));
            int steps = current.size();
            for (int i = 0; i < text.length(); i++) {
                current = advance(current, text.charAt(i));
                steps += current.size();
                if (current.isEmpty()) {
                    return new Run(false, steps);
                }
            }
            return new Run(current.contains(finalState), steps);
        }

        /**
         * One pass: each live state carries the earliest start that reaches it, and the live list
         * stays ordered by start. After a match, later starts are dropped and the scan goes on while
         * a state with that start or an earlier one is alive.
         */
        int[] leftmostLongest(String text) {
            int[] best = null;
            List<int[]> live = new ArrayList<>();
            for (int position = 0; position <= text.length(); position++) {
                if (best == null) {
                    boolean[] have = new boolean[kind.size()];
                    for (int[] entry : live) {
                        have[entry[0]] = true;
                    }
                    for (int state : closure(List.of(0))) {
                        if (!have[state]) {
                            live.add(new int[] {state, position});
                        }
                    }
                }
                for (int[] entry : live) {
                    if (entry[0] == finalState && (best == null || entry[1] <= best[0])) {
                        best = new int[] {entry[1], position};
                    }
                }
                if (best != null) {
                    int limit = best[0];
                    live.removeIf(entry -> entry[1] > limit);
                }
                if (position == text.length() || live.isEmpty()) {
                    break;
                }
                boolean[] seen = new boolean[kind.size()];
                List<int[]> moved = new ArrayList<>();
                for (int[] entry : live) {
                    if (!accepts(entry[0], text.charAt(position))) {
                        continue;
                    }
                    for (int reached : closure(List.of(outs.get(entry[0])[0]))) {
                        if (!seen[reached]) {
                            seen[reached] = true;
                            moved.add(new int[] {reached, entry[1]});
                        }
                    }
                }
                live = moved;
            }
            return best == null ? new int[] {-1, -1} : best;
        }
    }
}
