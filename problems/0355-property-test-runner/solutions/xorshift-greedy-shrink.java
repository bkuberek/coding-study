import java.util.*;
import java.util.function.Function;

/**
 * Generators are prefix token lists parsed into a small tree. One xorshift32 stream feeds a whole
 * call, so every value is fixed by the seed and its position. Shrinking is greedy: from the
 * failing value, take the first candidate that still fails, and start again from it, until no
 * candidate fails. Candidates are built from the generator, so each one is a value the generator
 * could have drawn: in range, long enough and through every filter. The stateful level runs each
 * command sequence on the correct queue and on the buggy one and shrinks the sequence the same
 * way, keeping only sequences whose commands are all allowed.
 */
public class PropertyRunner {
    private sealed interface Gen permits IntGen, ListGen, PairGen, FilterGen {
    }

    private record IntGen(int low, int high) implements Gen {
    }

    private record ListGen(int min, int max, Gen element) implements Gen {
    }

    private record PairGen(Gen first, Gen second) implements Gen {
    }

    private record FilterGen(String name, Gen inner) implements Gen {
    }

    private sealed interface Value permits IntValue, ListValue, PairValue {
    }

    private record IntValue(int value) implements Value {
    }

    private record ListValue(List<Value> items) implements Value {
    }

    private record PairValue(Value first, Value second) implements Value {
    }

    private static final class GiveUp extends RuntimeException {
        GiveUp() {
            super(null, null, false, false);
        }
    }

    private static final class RandomStream {
        private int state;
        private int discards;
        private final int limit;

        RandomStream(int seed, int limit) {
            this.state = seed;
            this.limit = limit;
        }

        long next() {
            int x = state;
            x ^= x << 13;
            x ^= x >>> 17;
            x ^= x << 5;
            state = x;
            return Integer.toUnsignedLong(x);
        }

        int between(int low, int high) {
            return (int) (low + next() % ((long) high - low + 1));
        }

        void discard() {
            discards++;
            if (discards > limit) {
                throw new GiveUp();
            }
        }
    }

    private record Parsed(Gen gen, int end) {
    }

    private static Parsed parse(String[] tokens, int at) {
        switch (tokens[at]) {
            case "int": {
                int low = Integer.parseInt(tokens[at + 1]);
                int high = Integer.parseInt(tokens[at + 2]);
                return new Parsed(new IntGen(low, high), at + 3);
            }
            case "list": {
                int min = Integer.parseInt(tokens[at + 1]);
                int max = Integer.parseInt(tokens[at + 2]);
                Parsed element = parse(tokens, at + 3);
                return new Parsed(new ListGen(min, max, element.gen()), element.end());
            }
            case "pair": {
                Parsed first = parse(tokens, at + 1);
                Parsed second = parse(tokens, first.end());
                return new Parsed(new PairGen(first.gen(), second.gen()), second.end());
            }
            default: {
                Parsed inner = parse(tokens, at + 2);
                return new Parsed(new FilterGen(tokens[at + 1], inner.gen()), inner.end());
            }
        }
    }

    private static Gen generator(String text) {
        return parse(text.split(" "), 0).gen();
    }

    private static Value draw(Gen gen, RandomStream rng) {
        return switch (gen) {
            case IntGen g -> new IntValue(rng.between(g.low(), g.high()));
            case ListGen g -> {
                int length = rng.between(g.min(), g.max());
                List<Value> items = new ArrayList<>();
                for (int i = 0; i < length; i++) {
                    items.add(draw(g.element(), rng));
                }
                yield new ListValue(items);
            }
            case PairGen g -> {
                Value first = draw(g.first(), rng);
                yield new PairValue(first, draw(g.second(), rng));
            }
            case FilterGen g -> {
                while (true) {
                    Value value = draw(g.inner(), rng);
                    if (passesFilter(g.name(), value)) {
                        yield value;
                    }
                    rng.discard();
                }
            }
        };
    }

    private static String text(Value value) {
        return switch (value) {
            case IntValue v -> Integer.toString(v.value());
            case ListValue v -> {
                StringJoiner joiner = new StringJoiner(",", "[", "]");
                for (Value item : v.items()) {
                    joiner.add(text(item));
                }
                yield joiner.toString();
            }
            case PairValue v -> "(" + text(v.first()) + "," + text(v.second()) + ")";
        };
    }

    private static int number(Value value) {
        return ((IntValue) value).value();
    }

    private static List<Value> items(Value value) {
        return ((ListValue) value).items();
    }

    private static boolean passesFilter(String name, Value value) {
        switch (name) {
            case "even":
                return number(value) % 2 == 0;
            case "odd":
                return number(value) % 2 != 0;
            case "nonzero":
                return number(value) != 0;
            case "positive":
                return number(value) > 0;
            case "nonempty":
                return !items(value).isEmpty();
            case "distinct": {
                Set<String> seen = new HashSet<>();
                for (Value item : items(value)) {
                    seen.add(text(item));
                }
                return seen.size() == items(value).size();
            }
            default: {
                PairValue pair = (PairValue) value;
                return !text(pair.first()).equals(text(pair.second()));
            }
        }
    }

    private static int total(Value value) {
        return switch (value) {
            case IntValue v -> v.value();
            case ListValue v -> {
                int sum = 0;
                for (Value item : v.items()) {
                    sum += total(item);
                }
                yield sum;
            }
            case PairValue v -> total(v.first()) + total(v.second());
        };
    }

    private static List<Integer> numbers(Value value) {
        List<Integer> result = new ArrayList<>();
        for (Value item : items(value)) {
            result.add(number(item));
        }
        return result;
    }

    private static boolean ordered(List<Integer> values) {
        for (int i = 0; i + 1 < values.size(); i++) {
            if (values.get(i) > values.get(i + 1)) {
                return false;
            }
        }
        return true;
    }

    private static boolean holds(String prop, Value value) {
        String[] parts = prop.split(" ");
        int k = parts.length > 1 ? Integer.parseInt(parts[1]) : 0;
        switch (parts[0]) {
            case "lt":
                return number(value) < k;
            case "not-multiple":
                return number(value) % k != 0;
            case "sum-lt":
                return total(value) < k;
            case "len-lt":
                return items(value).size() < k;
            case "ordered":
                return ordered(numbers(value));
            case "sort-ordered": {
                List<Integer> sorted = numbers(value);
                Collections.sort(sorted);
                return ordered(sorted);
            }
            case "one-pass-ordered": {
                List<Integer> list = numbers(value);
                for (int i = 0; i + 1 < list.size(); i++) {
                    if (list.get(i) > list.get(i + 1)) {
                        Collections.swap(list, i, i + 1);
                    }
                }
                return ordered(list);
            }
            case "max-from-zero": {
                List<Integer> list = numbers(value);
                int best = 0;
                for (int item : list) {
                    best = Math.max(best, item);
                }
                return list.isEmpty() || best == Collections.max(list);
            }
            case "keys-distinct": {
                Set<String> keys = new HashSet<>();
                for (Value item : items(value)) {
                    keys.add(text(((PairValue) item).first()));
                }
                return keys.size() == items(value).size();
            }
            default: {
                Map<String, String> first = new HashMap<>();
                Map<String, String> last = new HashMap<>();
                for (Value item : items(value)) {
                    PairValue pair = (PairValue) item;
                    String key = text(pair.first());
                    first.putIfAbsent(key, text(pair.second()));
                    last.put(key, text(pair.second()));
                }
                return first.equals(last);
            }
        }
    }

    private static List<Integer> intCandidates(int low, int high, int value) {
        int target = low > 0 ? low : high < 0 ? high : 0;
        List<Integer> found = new ArrayList<>();
        if (value == target) {
            return found;
        }
        found.add(target);
        for (int step = (value - target) / 2; step != 0; step /= 2) {
            found.add(value - step);
        }
        return found;
    }

    private static <T> List<T> withoutRepeats(T value, List<T> found, Function<T, String> show) {
        Set<String> seen = new HashSet<>();
        seen.add(show.apply(value));
        List<T> kept = new ArrayList<>();
        for (T candidate : found) {
            if (seen.add(show.apply(candidate))) {
                kept.add(candidate);
            }
        }
        return kept;
    }

    private static <T> List<List<T>> removals(List<T> items, int shortest) {
        int n = items.size();
        List<List<T>> found = new ArrayList<>();
        for (int size = n; size >= 1; size /= 2) {
            if (n - size < shortest) {
                continue;
            }
            for (int start = 0; start + size <= n; start += size) {
                List<T> shorter = new ArrayList<>(items.subList(0, start));
                shorter.addAll(items.subList(start + size, n));
                found.add(shorter);
            }
        }
        return found;
    }

    private static <T> List<T> replaced(List<T> items, int index, T item) {
        List<T> copy = new ArrayList<>(items);
        copy.set(index, item);
        return copy;
    }

    private static List<Value> candidatesOf(Gen gen, Value value) {
        List<Value> found = new ArrayList<>();
        switch (gen) {
            case IntGen g -> {
                for (int smaller : intCandidates(g.low(), g.high(), number(value))) {
                    found.add(new IntValue(smaller));
                }
            }
            case ListGen g -> {
                List<Value> list = items(value);
                for (List<Value> shorter : removals(list, g.min())) {
                    found.add(new ListValue(shorter));
                }
                for (int i = 0; i < list.size(); i++) {
                    for (Value smaller : candidatesOf(g.element(), list.get(i))) {
                        found.add(new ListValue(replaced(list, i, smaller)));
                    }
                }
            }
            case PairGen g -> {
                PairValue pair = (PairValue) value;
                for (Value smaller : candidatesOf(g.first(), pair.first())) {
                    found.add(new PairValue(smaller, pair.second()));
                }
                for (Value smaller : candidatesOf(g.second(), pair.second())) {
                    found.add(new PairValue(pair.first(), smaller));
                }
            }
            case FilterGen g -> {
                for (Value candidate : candidatesOf(g.inner(), value)) {
                    if (passesFilter(g.name(), candidate)) {
                        found.add(candidate);
                    }
                }
            }
        }
        return withoutRepeats(value, found, PropertyRunner::text);
    }

    private static final class BoundedQueue {
        private final int capacity;
        private final String bug;
        private final Deque<Integer> items = new ArrayDeque<>();
        private int puts;

        BoundedQueue(int capacity, String bug) {
            this.capacity = capacity;
            this.bug = bug;
        }

        boolean allows(String command) {
            return !command.equals("get") || !items.isEmpty();
        }

        String apply(String command) {
            if (command.equals("size")) {
                int count = items.size();
                return Integer.toString(bug.equals("size-wraps") ? count % capacity : count);
            }
            if (command.equals("get")) {
                if (items.isEmpty()) {
                    return "empty";
                }
                if (bug.equals("wrap-lifo") && puts > capacity) {
                    return Integer.toString(items.removeLast());
                }
                return Integer.toString(items.removeFirst());
            }
            int value = Integer.parseInt(command.substring(4));
            if (items.size() == capacity) {
                if (!bug.equals("full-overwrites")) {
                    return "full";
                }
                items.removeFirst();
            } else if (bug.equals("repeat-dropped") && !items.isEmpty() && items.peekLast() == value) {
                puts++;
                return "ok";
            }
            items.addLast(value);
            puts++;
            return "ok";
        }
    }

    private static boolean valid(int capacity, List<String> commands) {
        BoundedQueue model = new BoundedQueue(capacity, "none");
        for (String command : commands) {
            if (!model.allows(command)) {
                return false;
            }
            model.apply(command);
        }
        return true;
    }

    private static boolean fails(int capacity, String bug, List<String> commands) {
        BoundedQueue model = new BoundedQueue(capacity, "none");
        BoundedQueue system = new BoundedQueue(capacity, bug);
        for (String command : commands) {
            if (!model.apply(command).equals(system.apply(command))) {
                return true;
            }
        }
        return false;
    }

    private static List<String> sequence(int capacity, RandomStream rng, int longest) {
        BoundedQueue model = new BoundedQueue(capacity, "none");
        List<String> commands = new ArrayList<>();
        int length = rng.between(1, longest);
        for (int i = 0; i < length; i++) {
            List<String> allowed =
                    model.items.isEmpty() ? List.of("put", "size") : List.of("put", "get", "size");
            String command = allowed.get((int) (rng.next() % allowed.size()));
            if (command.equals("put")) {
                command = "put " + rng.between(0, 9);
            }
            model.apply(command);
            commands.add(command);
        }
        return commands;
    }

    private static List<List<String>> sequenceCandidates(int capacity, List<String> commands) {
        List<List<String>> found = removals(commands, 1);
        for (int i = 0; i < commands.size(); i++) {
            String command = commands.get(i);
            if (command.startsWith("put ")) {
                for (int smaller : intCandidates(0, 9, Integer.parseInt(command.substring(4)))) {
                    found.add(replaced(commands, i, "put " + smaller));
                }
            }
        }
        List<List<String>> kept = new ArrayList<>();
        for (List<String> candidate : withoutRepeats(commands, found, c -> String.join(", ", c))) {
            if (valid(capacity, candidate)) {
                kept.add(candidate);
            }
        }
        return kept;
    }

    private record Outcome(String kind, int run, Value value) {
    }

    private int limit = 100;

    public PropertyRunner() {
    }

    // Level 1
    public List<Long> randoms(int seed, int count) {
        RandomStream rng = new RandomStream(seed, limit);
        List<Long> numbers = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            numbers.add(rng.next());
        }
        return numbers;
    }

    public List<String> generate(String gen, int seed, int count) {
        RandomStream rng = new RandomStream(seed, limit);
        Gen parsed = generator(gen);
        List<String> values = new ArrayList<>();
        try {
            for (int i = 0; i < count; i++) {
                values.add(text(draw(parsed, rng)));
            }
        } catch (GiveUp stop) {
            // the values completed before the limit are the answer
        }
        return values;
    }

    public String check(String gen, String prop, int seed, int runs) {
        Outcome outcome = search(gen, prop, seed, runs);
        return switch (outcome.kind()) {
            case "failed" -> "failed " + outcome.run() + ": " + text(outcome.value());
            case "gave up" -> "gave up after " + outcome.run();
            default -> "passed " + runs;
        };
    }

    // Level 2
    public List<String> candidates(String gen, int seed, int index) {
        RandomStream rng = new RandomStream(seed, limit);
        Gen parsed = generator(gen);
        Value value = null;
        try {
            for (int i = 0; i < index; i++) {
                value = draw(parsed, rng);
            }
        } catch (GiveUp stop) {
            return new ArrayList<>();
        }
        List<String> result = new ArrayList<>();
        for (Value candidate : candidatesOf(parsed, value)) {
            result.add(text(candidate));
        }
        return result;
    }

    public List<String> minimize(String gen, String prop, int seed, int runs) {
        Outcome outcome = search(gen, prop, seed, runs);
        List<String> path = new ArrayList<>();
        if (!outcome.kind().equals("failed")) {
            return path;
        }
        Gen parsed = generator(gen);
        Value value = outcome.value();
        path.add(text(value));
        while (true) {
            Value smaller = null;
            for (Value candidate : candidatesOf(parsed, value)) {
                if (!holds(prop, candidate)) {
                    smaller = candidate;
                    break;
                }
            }
            if (smaller == null) {
                return path;
            }
            value = smaller;
            path.add(text(value));
        }
    }

    // Level 3
    public void setDiscardLimit(int limit) {
        this.limit = limit;
    }

    // Level 4
    public List<String> replay(int capacity, String bug, List<String> commands) {
        BoundedQueue model = new BoundedQueue(capacity, "none");
        BoundedQueue system = new BoundedQueue(capacity, bug);
        List<String> answers = new ArrayList<>();
        for (String command : commands) {
            if (!model.allows(command)) {
                answers.add("invalid");
                break;
            }
            model.apply(command);
            answers.add(system.apply(command));
        }
        return answers;
    }

    public List<String> generateCommands(int capacity, int seed, int count, int maxLength) {
        RandomStream rng = new RandomStream(seed, limit);
        List<String> sequences = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            sequences.add(String.join(", ", sequence(capacity, rng, maxLength)));
        }
        return sequences;
    }

    public List<String> firstFailure(int capacity, String bug, int seed, int runs, int maxLength) {
        RandomStream rng = new RandomStream(seed, limit);
        for (int i = 0; i < runs; i++) {
            List<String> commands = sequence(capacity, rng, maxLength);
            if (fails(capacity, bug, commands)) {
                return commands;
            }
        }
        return new ArrayList<>();
    }

    public List<String> shrinkFailure(int capacity, String bug, int seed, int runs, int maxLength) {
        List<String> commands = firstFailure(capacity, bug, seed, runs, maxLength);
        while (!commands.isEmpty()) {
            List<String> smaller = null;
            for (List<String> candidate : sequenceCandidates(capacity, commands)) {
                if (fails(capacity, bug, candidate)) {
                    smaller = candidate;
                    break;
                }
            }
            if (smaller == null) {
                break;
            }
            commands = smaller;
        }
        return commands;
    }

    private Outcome search(String gen, String prop, int seed, int runs) {
        RandomStream rng = new RandomStream(seed, limit);
        Gen parsed = generator(gen);
        int passed = 0;
        try {
            for (int run = 1; run <= runs; run++) {
                Value value = draw(parsed, rng);
                if (!holds(prop, value)) {
                    return new Outcome("failed", run, value);
                }
                passed++;
            }
        } catch (GiveUp stop) {
            return new Outcome("gave up", passed, null);
        }
        return new Outcome("passed", runs, null);
    }
}
