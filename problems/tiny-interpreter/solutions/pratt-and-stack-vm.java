import java.util.*;

public class Interpreter {
    private static final Set<String> KEYWORDS = Set.of("let", "in", "fn", "if", "then", "else");
    private static final Set<String> TWO_CHAR_SYMBOLS = Set.of("==", "!=", "<=", ">=", "=>");
    private static final String ONE_CHAR_SYMBOLS = "()+-*/%^<>=,";
    private static final long INT_MIN = Integer.MIN_VALUE;
    private static final long INT_MAX = Integer.MAX_VALUE;
    /** Binding power of each binary operator; {@code ^} groups to the right. */
    private static final Map<String, Integer> BINARY = Map.ofEntries(
            Map.entry("==", 1), Map.entry("!=", 1), Map.entry("<", 1), Map.entry("<=", 1),
            Map.entry(">", 1), Map.entry(">=", 1), Map.entry("+", 2), Map.entry("-", 2),
            Map.entry("*", 3), Map.entry("/", 3), Map.entry("%", 3), Map.entry("^", 5));
    private static final int PREFIX_MINUS = 4;
    private static final int CALL = 6;
    private static final int LOWEST = 0;
    private static final Map<String, String> OPCODES = Map.ofEntries(
            Map.entry("+", "ADD"), Map.entry("-", "SUB"), Map.entry("*", "MUL"), Map.entry("/", "DIV"),
            Map.entry("%", "MOD"), Map.entry("^", "POW"), Map.entry("==", "EQ"), Map.entry("!=", "NE"),
            Map.entry("<", "LT"), Map.entry("<=", "LE"), Map.entry(">", "GT"), Map.entry(">=", "GE"));
    private static final Map<String, String> OPERATORS = new HashMap<>();

    static {
        OPCODES.forEach((operator, opcode) -> OPERATORS.put(opcode, operator));
    }

    private static final class LangError extends RuntimeException {
        final String code;
        final int line;
        final int column;

        LangError(String code, int[] position) {
            super(code, null, false, false);
            this.code = code;
            this.line = position[0];
            this.column = position[1];
        }

        String text() {
            return "error " + code + " " + line + ":" + column;
        }
    }

    private record Token(String kind, String text, int[] position) {
        String describe() {
            String where = position[0] + ":" + position[1];
            return kind.equals("end") ? "end " + where : kind + " " + text + " " + where;
        }
    }

    // ------------------------------------------------------------------------ level 1: tokens
    private static boolean isDigit(char c) {
        return c >= '0' && c <= '9';
    }

    private static boolean isLetter(char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_';
    }

    private static List<Token> scan(String source) {
        List<Token> tokens = new ArrayList<>();
        int index = 0;
        int line = 1;
        int column = 1;
        while (index < source.length()) {
            char c = source.charAt(index);
            int[] here = {line, column};
            int length;
            if (c == '\n') {
                index++;
                line++;
                column = 1;
                continue;
            } else if (c == ' ' || c == '\t') {
                length = 1;
            } else if (c == '#') {
                int end = index;
                while (end < source.length() && source.charAt(end) != '\n') {
                    end++;
                }
                length = end - index;
            } else if (isDigit(c)) {
                int end = index;
                while (end < source.length() && isDigit(source.charAt(end))) {
                    end++;
                }
                String digits = source.substring(index, end);
                boolean leadingZero = digits.length() > 1 && digits.charAt(0) == '0';
                if (leadingZero || digits.length() > 10 || Long.parseLong(digits) > INT_MAX) {
                    throw new LangError("bad-number", here);
                }
                tokens.add(new Token("number", digits, here));
                length = end - index;
            } else if (isLetter(c)) {
                int end = index;
                while (end < source.length() && (isLetter(source.charAt(end)) || isDigit(source.charAt(end)))) {
                    end++;
                }
                String word = source.substring(index, end);
                tokens.add(new Token(KEYWORDS.contains(word) ? "keyword" : "name", word, here));
                length = end - index;
            } else if (index + 2 <= source.length() && TWO_CHAR_SYMBOLS.contains(source.substring(index, index + 2))) {
                tokens.add(new Token("symbol", source.substring(index, index + 2), here));
                length = 2;
            } else if (ONE_CHAR_SYMBOLS.indexOf(c) >= 0) {
                tokens.add(new Token("symbol", String.valueOf(c), here));
                length = 1;
            } else {
                throw new LangError("bad-char", here);
            }
            index += length;
            column += length;
        }
        tokens.add(new Token("end", "", new int[] {line, column}));
        return tokens;
    }

    // ------------------------------------------------------------------------ level 2: syntax tree
    private sealed interface Node permits Num, Name, Negate, Binary, Call, Let, If, Fn {
        int[] position();
    }

    private record Num(int[] position, int value) implements Node {}

    private record Name(int[] position, String name) implements Node {}

    private record Negate(int[] position, Node operand) implements Node {}

    private record Binary(int[] position, String operator, Node left, Node right) implements Node {}

    private record Call(int[] position, Node callee, List<Node> args) implements Node {}

    private record Let(int[] position, String name, Node value, Node body) implements Node {}

    private record If(int[] position, Node condition, Node then, Node otherwise) implements Node {}

    private record Fn(int[] position, String name, List<String> params, Node body, int block) implements Node {}

    /**
     * A Pratt parser: each token knows how it starts an expression (prefix) and how it continues one
     * (infix), and {@code expression(minimum)} extends the left side while the next operator binds tighter.
     */
    private static final class Parser {
        private final List<Token> tokens;
        private int index = 0;
        private int functions = 0;

        Parser(List<Token> tokens) {
            this.tokens = tokens;
        }

        Node program() {
            Node node = expression(LOWEST);
            expect("end", null);
            return node;
        }

        private Token peek() {
            return tokens.get(index);
        }

        private Token take() {
            return tokens.get(index++);
        }

        private boolean peekSymbol(String text) {
            return peek().kind().equals("symbol") && peek().text().equals(text);
        }

        private Token expect(String kind, String text) {
            Token token = peek();
            if (!token.kind().equals(kind) || (text != null && !token.text().equals(text))) {
                throw new LangError("unexpected-token", token.position());
            }
            return take();
        }

        private Node expression(int minimum) {
            Node left = prefix();
            while (true) {
                Token token = peek();
                if (!token.kind().equals("symbol")) {
                    return left;
                }
                Integer power = BINARY.get(token.text());
                if (token.text().equals("(") && CALL > minimum) {
                    left = call(left);
                } else if (power != null && power > minimum) {
                    take();
                    Node right = expression(token.text().equals("^") ? power - 1 : power);
                    left = new Binary(token.position(), token.text(), left, right);
                } else {
                    return left;
                }
            }
        }

        private Node prefix() {
            Token token = take();
            String kind = token.kind();
            String text = token.text();
            if (kind.equals("number")) {
                return new Num(token.position(), Integer.parseInt(text));
            }
            if (kind.equals("name")) {
                return new Name(token.position(), text);
            }
            if (kind.equals("symbol") && text.equals("-")) {
                return new Negate(token.position(), expression(PREFIX_MINUS));
            }
            if (kind.equals("symbol") && text.equals("(")) {
                Node inner = expression(LOWEST);
                expect("symbol", ")");
                return inner;
            }
            if (kind.equals("keyword") && text.equals("let")) {
                String name = expect("name", null).text();
                expect("symbol", "=");
                Node value = expression(LOWEST);
                expect("keyword", "in");
                return new Let(token.position(), name, value, expression(LOWEST));
            }
            if (kind.equals("keyword") && text.equals("if")) {
                Node condition = expression(LOWEST);
                expect("keyword", "then");
                Node then = expression(LOWEST);
                expect("keyword", "else");
                return new If(token.position(), condition, then, expression(LOWEST));
            }
            if (kind.equals("keyword") && text.equals("fn")) {
                return function(token);
            }
            throw new LangError("unexpected-token", token.position());
        }

        private Fn function(Token keyword) {
            int block = ++functions;
            String name = peek().kind().equals("name") ? take().text() : null;
            expect("symbol", "(");
            List<String> params = new ArrayList<>();
            if (!peekSymbol(")")) {
                while (true) {
                    Token param = expect("name", null);
                    if (params.contains(param.text())) {
                        throw new LangError("duplicate-param", param.position());
                    }
                    params.add(param.text());
                    if (!peekSymbol(",")) {
                        break;
                    }
                    take();
                }
            }
            expect("symbol", ")");
            expect("symbol", "=>");
            return new Fn(keyword.position(), name, params, expression(LOWEST), block);
        }

        private Node call(Node callee) {
            Token paren = take();
            List<Node> args = new ArrayList<>();
            if (!peekSymbol(")")) {
                args.add(expression(LOWEST));
                while (peekSymbol(",")) {
                    take();
                    args.add(expression(LOWEST));
                }
            }
            expect("symbol", ")");
            return new Call(paren.position(), callee, args);
        }
    }

    private static Node parseSource(String source) {
        return new Parser(scan(source)).program();
    }

    private static String head(Fn fn) {
        String named = fn.name() == null ? "fn " : "fn " + fn.name() + " ";
        return named + "(" + String.join(" ", fn.params()) + ")";
    }

    private static String show(Node node) {
        return switch (node) {
            case Num n -> Integer.toString(n.value());
            case Name n -> n.name();
            case Negate n -> "(neg " + show(n.operand()) + ")";
            case Binary n -> "(" + n.operator() + " " + show(n.left()) + " " + show(n.right()) + ")";
            case Call n -> {
                StringBuilder text = new StringBuilder("(call ").append(show(n.callee()));
                for (Node arg : n.args()) {
                    text.append(' ').append(show(arg));
                }
                yield text.append(')').toString();
            }
            case Let n -> "(let " + n.name() + " " + show(n.value()) + " " + show(n.body()) + ")";
            case If n -> "(if " + show(n.condition()) + " " + show(n.then()) + " " + show(n.otherwise()) + ")";
            case Fn n -> "(" + head(n) + " " + show(n.body()) + ")";
        };
    }

    // ------------------------------------------------------------------------ level 3: evaluation
    /** One level of names; lookups walk outwards to the enclosing levels. */
    private record Scope(Scope parent, Map<String, Object> names) {
        Object lookup(String name, int[] position) {
            for (Scope scope = this; scope != null; scope = scope.parent()) {
                Object value = scope.names().get(name);
                if (value != null) {
                    return value;
                }
            }
            throw new LangError("unbound", position);
        }
    }

    /** A function value; values are {@code Integer} or {@code Closure}. */
    private record Closure(String name, List<String> params, Scope scope, Node body, int block) {
        Scope callScope(List<Object> args) {
            Map<String, Object> names = new HashMap<>();
            if (name != null) {
                names.put(name, this);
            }
            for (int index = 0; index < params.size(); index++) {
                names.put(params.get(index), args.get(index));
            }
            return new Scope(scope, names);
        }

        @Override
        public String toString() {
            return name == null ? "<fn>" : "<fn " + name + ">";
        }
    }

    private static int checked(long value, int[] position) {
        if (value < INT_MIN || value > INT_MAX) {
            throw new LangError("overflow", position);
        }
        return (int) value;
    }

    private static int power(int base, int exponent, int[] position) {
        if ((base == 0 || base == 1) && exponent > 0) {
            return base;
        }
        if (base == -1) {
            return exponent % 2 == 1 ? -1 : 1;
        }
        int result = 1;
        for (int step = 0; step < exponent; step++) {
            result = checked((long) result * base, position);
        }
        return result;
    }

    private static int applyBinary(String operator, Object left, Object right, int[] position) {
        if (!(left instanceof Integer a) || !(right instanceof Integer b)) {
            throw new LangError("type", position);
        }
        if ((operator.equals("/") || operator.equals("%")) && b == 0) {
            throw new LangError("div-zero", position);
        }
        if (operator.equals("^") && b < 0) {
            throw new LangError("negative-exponent", position);
        }
        return switch (operator) {
            case "+" -> checked((long) a + b, position);
            case "-" -> checked((long) a - b, position);
            case "*" -> checked((long) a * b, position);
            case "/" -> checked((long) a / b, position);
            case "%" -> (int) ((long) a % b);
            case "^" -> power(a, b, position);
            case "==" -> a.intValue() == b.intValue() ? 1 : 0;
            case "!=" -> a.intValue() != b.intValue() ? 1 : 0;
            case "<" -> a < b ? 1 : 0;
            case "<=" -> a <= b ? 1 : 0;
            case ">" -> a > b ? 1 : 0;
            default -> a >= b ? 1 : 0;
        };
    }

    private static int negate(Object value, int[] position) {
        if (!(value instanceof Integer number)) {
            throw new LangError("type", position);
        }
        return checked(-(long) number, position);
    }

    private static Closure checkCall(Object callee, int count, int depth, int maxDepth, int[] position) {
        if (!(callee instanceof Closure closure)) {
            throw new LangError("not-callable", position);
        }
        if (count != closure.params().size()) {
            throw new LangError("arity", position);
        }
        if (depth >= maxDepth) {
            throw new LangError("depth", position);
        }
        return closure;
    }

    private static boolean truth(Object value, int[] position) {
        if (!(value instanceof Integer number)) {
            throw new LangError("type", position);
        }
        return number != 0;
    }

    private Object walk(Node node, Scope scope, int depth) {
        return switch (node) {
            case Num n -> n.value();
            case Name n -> scope.lookup(n.name(), n.position());
            case Negate n -> negate(walk(n.operand(), scope, depth), n.position());
            case Binary n -> {
                Object left = walk(n.left(), scope, depth);
                Object right = walk(n.right(), scope, depth);
                yield applyBinary(n.operator(), left, right, n.position());
            }
            case If n -> walk(truth(walk(n.condition(), scope, depth), n.position()) ? n.then() : n.otherwise(), scope, depth);
            case Let n -> {
                Object bound = walk(n.value(), scope, depth);
                Map<String, Object> names = new HashMap<>();
                names.put(n.name(), bound);
                yield walk(n.body(), new Scope(scope, names), depth);
            }
            case Fn n -> new Closure(n.name(), n.params(), scope, n.body(), n.block());
            case Call n -> {
                Object callee = walk(n.callee(), scope, depth);
                List<Object> values = new ArrayList<>();
                for (Node arg : n.args()) {
                    values.add(walk(arg, scope, depth));
                }
                Closure closure = checkCall(callee, values.size(), depth, maxDepth, n.position());
                yield walk(closure.body(), closure.callScope(values), depth + 1);
            }
        };
    }

    // ------------------------------------------------------------------------ level 4: bytecode
    private static final class Instruction {
        final String opcode;
        Object operand;
        final int[] position;

        Instruction(String opcode, Object operand, int[] position) {
            this.opcode = opcode;
            this.operand = operand;
            this.position = position;
        }

        String describe() {
            StringBuilder text = new StringBuilder(opcode);
            if (operand != null) {
                text.append(' ').append(operand);
            }
            if (position != null) {
                text.append(' ').append(position[0]).append(':').append(position[1]);
            }
            return text.toString();
        }
    }

    private record Block(String header, String name, List<String> params, List<Instruction> code) {}

    private static final class Compiler {
        private final Map<Integer, Block> blocks = new TreeMap<>();

        List<Block> program(Node node) {
            blocks.put(0, new Block("main", null, List.of(), new ArrayList<>()));
            emitBlock(0, node);
            return new ArrayList<>(blocks.values());
        }

        private void emitBlock(int number, Node body) {
            List<Instruction> code = blocks.get(number).code();
            emit(body, code);
            code.add(new Instruction("RETURN", null, null));
        }

        private void emit(Node node, List<Instruction> code) {
            switch (node) {
                case Num n -> code.add(new Instruction("PUSH", n.value(), null));
                case Name n -> code.add(new Instruction("LOAD", n.name(), n.position()));
                case Negate n -> {
                    emit(n.operand(), code);
                    code.add(new Instruction("NEG", null, n.position()));
                }
                case Binary n -> {
                    emit(n.left(), code);
                    emit(n.right(), code);
                    code.add(new Instruction(OPCODES.get(n.operator()), null, n.position()));
                }
                case If n -> {
                    emit(n.condition(), code);
                    Instruction toElse = new Instruction("JUMP_IF_ZERO", null, n.position());
                    code.add(toElse);
                    emit(n.then(), code);
                    Instruction toEnd = new Instruction("JUMP", null, null);
                    code.add(toEnd);
                    toElse.operand = code.size();
                    emit(n.otherwise(), code);
                    toEnd.operand = code.size();
                }
                case Let n -> {
                    emit(n.value(), code);
                    code.add(new Instruction("BIND", n.name(), null));
                    emit(n.body(), code);
                    code.add(new Instruction("UNBIND", null, null));
                }
                case Fn n -> {
                    blocks.put(n.block(), new Block(head(n), n.name(), n.params(), new ArrayList<>()));
                    emitBlock(n.block(), n.body());
                    code.add(new Instruction("CLOSURE", n.block(), null));
                }
                case Call n -> {
                    emit(n.callee(), code);
                    for (Node arg : n.args()) {
                        emit(arg, code);
                    }
                    code.add(new Instruction("CALL", n.args().size(), n.position()));
                }
            }
        }
    }

    private static final class Frame {
        final Block block;
        Scope scope;
        int ip = 0;

        Frame(Block block, Scope scope) {
            this.block = block;
            this.scope = scope;
        }
    }

    /**
     * A stack machine: one value stack shared by all frames, and a frame per active call. The loop
     * never recurses, so the depth limit is the only bound on calls.
     */
    private Object execute(List<Block> blocks) {
        Deque<Object> stack = new ArrayDeque<>();
        Deque<Frame> frames = new ArrayDeque<>();
        frames.push(new Frame(blocks.get(0), new Scope(null, Map.of())));
        while (true) {
            Frame frame = frames.peek();
            Instruction instruction = frame.block.code().get(frame.ip++);
            int[] position = instruction.position;
            String operator = OPERATORS.get(instruction.opcode);
            if (operator != null) {
                Object right = stack.pop();
                Object left = stack.pop();
                stack.push(applyBinary(operator, left, right, position));
                continue;
            }
            switch (instruction.opcode) {
                case "PUSH" -> stack.push(instruction.operand);
                case "LOAD" -> stack.push(frame.scope.lookup((String) instruction.operand, position));
                case "NEG" -> stack.push(negate(stack.pop(), position));
                case "JUMP_IF_ZERO" -> {
                    if (!truth(stack.pop(), position)) {
                        frame.ip = (Integer) instruction.operand;
                    }
                }
                case "JUMP" -> frame.ip = (Integer) instruction.operand;
                case "BIND" -> {
                    Map<String, Object> names = new HashMap<>();
                    names.put((String) instruction.operand, stack.pop());
                    frame.scope = new Scope(frame.scope, names);
                }
                case "UNBIND" -> frame.scope = frame.scope.parent();
                case "CLOSURE" -> {
                    int number = (Integer) instruction.operand;
                    Block block = blocks.get(number);
                    stack.push(new Closure(block.name(), block.params(), frame.scope, null, number));
                }
                case "CALL" -> {
                    int count = (Integer) instruction.operand;
                    List<Object> args = new ArrayList<>(Collections.nCopies(count, null));
                    for (int index = count - 1; index >= 0; index--) {
                        args.set(index, stack.pop());
                    }
                    Object callee = stack.pop();
                    Closure closure = checkCall(callee, count, frames.size() - 1, maxDepth, position);
                    frames.push(new Frame(blocks.get(closure.block()), closure.callScope(args)));
                }
                default -> {
                    frames.pop();
                    if (frames.isEmpty()) {
                        return stack.pop();
                    }
                }
            }
        }
    }

    private static List<String> listing(List<Block> blocks) {
        List<String> lines = new ArrayList<>();
        for (int number = 0; number < blocks.size(); number++) {
            Block block = blocks.get(number);
            lines.add("block " + number + " " + block.header());
            for (int index = 0; index < block.code().size(); index++) {
                lines.add(index + " " + block.code().get(index).describe());
            }
        }
        return lines;
    }

    private final int maxDepth;

    public Interpreter(int maxDepth) {
        this.maxDepth = maxDepth;
    }

    // Level 1
    public List<String> tokenize(String source) {
        try {
            List<String> lines = new ArrayList<>();
            for (Token token : scan(source)) {
                lines.add(token.describe());
            }
            return lines;
        } catch (LangError error) {
            return List.of(error.text());
        }
    }

    // Level 2
    public String parse(String source) {
        try {
            return show(parseSource(source));
        } catch (LangError error) {
            return error.text();
        }
    }

    // Level 3
    public String evaluate(String source) {
        try {
            return walk(parseSource(source), new Scope(null, Map.of()), 0).toString();
        } catch (LangError error) {
            return error.text();
        }
    }

    // Level 4
    public List<String> bytecode(String source) {
        try {
            return listing(new Compiler().program(parseSource(source)));
        } catch (LangError error) {
            return List.of(error.text());
        }
    }

    public String run(String source) {
        try {
            return execute(new Compiler().program(parseSource(source))).toString();
        } catch (LangError error) {
            return error.text();
        }
    }
}
