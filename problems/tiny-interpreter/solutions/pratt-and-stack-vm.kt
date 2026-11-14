private val KEYWORDS = setOf("let", "in", "fn", "if", "then", "else")
private val TWO_CHAR_SYMBOLS = setOf("==", "!=", "<=", ">=", "=>")
private const val ONE_CHAR_SYMBOLS = "()+-*/%^<>=,"
private const val INT_MIN = -2147483648L
private const val INT_MAX = 2147483647L

/** Binding power of each binary operator; `^` groups to the right. */
private val BINARY = mapOf(
    "==" to 1, "!=" to 1, "<" to 1, "<=" to 1, ">" to 1, ">=" to 1,
    "+" to 2, "-" to 2,
    "*" to 3, "/" to 3, "%" to 3,
    "^" to 5,
)
private const val PREFIX_MINUS = 4
private const val CALL = 6
private const val LOWEST = 0
private val OPCODES = mapOf(
    "+" to "ADD", "-" to "SUB", "*" to "MUL", "/" to "DIV", "%" to "MOD", "^" to "POW",
    "==" to "EQ", "!=" to "NE", "<" to "LT", "<=" to "LE", ">" to "GT", ">=" to "GE",
)
private val OPERATORS = OPCODES.entries.associate { (operator, opcode) -> opcode to operator }

private data class Position(val line: Int, val column: Int) {
    override fun toString() = "$line:$column"
}

private class LangError(val code: String, val position: Position) : RuntimeException(code, null, false, false) {
    fun text() = "error $code $position"
}

private class Token(val kind: String, val text: String, val position: Position) {
    fun describe() = if (kind == "end") "end $position" else "$kind $text $position"
}

// ------------------------------------------------------------------------------ level 1: tokens
private fun Char.isAsciiDigit() = this in '0'..'9'

private fun Char.startsName() = this in 'a'..'z' || this in 'A'..'Z' || this == '_'

private fun scan(source: String): List<Token> {
    val tokens = mutableListOf<Token>()
    var index = 0
    var line = 1
    var column = 1
    while (index < source.length) {
        val char = source[index]
        val here = Position(line, column)
        if (char == '\n') {
            index++
            line++
            column = 1
            continue
        }
        val length = when {
            char == ' ' || char == '\t' -> 1
            char == '#' -> (source.indexOf('\n', index).takeIf { it >= 0 } ?: source.length) - index
            char.isAsciiDigit() -> {
                var end = index
                while (end < source.length && source[end].isAsciiDigit()) end++
                val digits = source.substring(index, end)
                val leadingZero = digits.length > 1 && digits[0] == '0'
                if (leadingZero || digits.length > 10 || digits.toLong() > INT_MAX) throw LangError("bad-number", here)
                tokens.add(Token("number", digits, here))
                end - index
            }
            char.startsName() -> {
                var end = index
                while (end < source.length && (source[end].startsName() || source[end].isAsciiDigit())) end++
                val word = source.substring(index, end)
                tokens.add(Token(if (word in KEYWORDS) "keyword" else "name", word, here))
                end - index
            }
            index + 2 <= source.length && source.substring(index, index + 2) in TWO_CHAR_SYMBOLS -> {
                tokens.add(Token("symbol", source.substring(index, index + 2), here))
                2
            }
            char in ONE_CHAR_SYMBOLS -> {
                tokens.add(Token("symbol", char.toString(), here))
                1
            }
            else -> throw LangError("bad-char", here)
        }
        index += length
        column += length
    }
    tokens.add(Token("end", "", Position(line, column)))
    return tokens
}

// ------------------------------------------------------------------------------ level 2: syntax tree
private sealed class Node(val position: Position)
private class Num(position: Position, val value: Int) : Node(position)
private class Name(position: Position, val name: String) : Node(position)
private class Negate(position: Position, val operand: Node) : Node(position)
private class Binary(position: Position, val operator: String, val left: Node, val right: Node) : Node(position)
private class Call(position: Position, val callee: Node, val args: List<Node>) : Node(position)
private class Let(position: Position, val name: String, val value: Node, val body: Node) : Node(position)
private class If(position: Position, val condition: Node, val then: Node, val otherwise: Node) : Node(position)
private class Fn(position: Position, val name: String?, val params: List<String>, val body: Node, val block: Int) :
    Node(position)

/**
 * A Pratt parser: each token knows how it starts an expression (prefix) and how it continues one
 * (infix), and [expression] extends the left side while the next operator binds tighter.
 */
private class Parser(private val tokens: List<Token>) {
    private var index = 0
    private var functions = 0

    fun program(): Node {
        val node = expression(LOWEST)
        expect("end")
        return node
    }

    private fun peek() = tokens[index]

    private fun take() = tokens[index++]

    private fun peekSymbol(text: String) = peek().kind == "symbol" && peek().text == text

    private fun expect(kind: String, text: String? = null): Token {
        val token = peek()
        if (token.kind != kind || (text != null && token.text != text)) {
            throw LangError("unexpected-token", token.position)
        }
        return take()
    }

    private fun expression(minimum: Int): Node {
        var left = prefix()
        while (true) {
            val token = peek()
            if (token.kind != "symbol") return left
            val power = BINARY[token.text]
            left = when {
                token.text == "(" && CALL > minimum -> call(left)
                power != null && power > minimum -> {
                    take()
                    val right = expression(if (token.text == "^") power - 1 else power)
                    Binary(token.position, token.text, left, right)
                }
                else -> return left
            }
        }
    }

    private fun prefix(): Node {
        val token = take()
        return when {
            token.kind == "number" -> Num(token.position, token.text.toInt())
            token.kind == "name" -> Name(token.position, token.text)
            token.kind == "symbol" && token.text == "-" -> Negate(token.position, expression(PREFIX_MINUS))
            token.kind == "symbol" && token.text == "(" -> expression(LOWEST).also { expect("symbol", ")") }
            token.kind == "keyword" && token.text == "let" -> {
                val name = expect("name").text
                expect("symbol", "=")
                val value = expression(LOWEST)
                expect("keyword", "in")
                Let(token.position, name, value, expression(LOWEST))
            }
            token.kind == "keyword" && token.text == "if" -> {
                val condition = expression(LOWEST)
                expect("keyword", "then")
                val then = expression(LOWEST)
                expect("keyword", "else")
                If(token.position, condition, then, expression(LOWEST))
            }
            token.kind == "keyword" && token.text == "fn" -> function(token)
            else -> throw LangError("unexpected-token", token.position)
        }
    }

    private fun function(keyword: Token): Fn {
        val block = ++functions
        val name = if (peek().kind == "name") take().text else null
        expect("symbol", "(")
        val params = mutableListOf<String>()
        if (!peekSymbol(")")) {
            while (true) {
                val param = expect("name")
                if (param.text in params) throw LangError("duplicate-param", param.position)
                params.add(param.text)
                if (!peekSymbol(",")) break
                take()
            }
        }
        expect("symbol", ")")
        expect("symbol", "=>")
        return Fn(keyword.position, name, params, expression(LOWEST), block)
    }

    private fun call(callee: Node): Node {
        val paren = take()
        val args = mutableListOf<Node>()
        if (!peekSymbol(")")) {
            args.add(expression(LOWEST))
            while (peekSymbol(",")) {
                take()
                args.add(expression(LOWEST))
            }
        }
        expect("symbol", ")")
        return Call(paren.position, callee, args)
    }
}

private fun parseProgram(source: String): Node = Parser(scan(source)).program()

private fun head(fn: Fn): String {
    val named = if (fn.name == null) "fn " else "fn ${fn.name} "
    return named + fn.params.joinToString(" ", "(", ")")
}

private fun show(node: Node): String = when (node) {
    is Num -> node.value.toString()
    is Name -> node.name
    is Negate -> "(neg ${show(node.operand)})"
    is Binary -> "(${node.operator} ${show(node.left)} ${show(node.right)})"
    is Call -> (listOf("call", show(node.callee)) + node.args.map(::show)).joinToString(" ", "(", ")")
    is Let -> "(let ${node.name} ${show(node.value)} ${show(node.body)})"
    is If -> "(if ${show(node.condition)} ${show(node.then)} ${show(node.otherwise)})"
    is Fn -> "(${head(node)} ${show(node.body)})"
}

// ------------------------------------------------------------------------------ level 3: evaluation
/** One level of names; lookups walk outwards to the enclosing levels. Values are `Int` or [Closure]. */
private class Scope(val parent: Scope?, val names: Map<String, Any>) {
    fun lookup(name: String, position: Position): Any {
        var scope: Scope? = this
        while (scope != null) {
            scope.names[name]?.let { return it }
            scope = scope.parent
        }
        throw LangError("unbound", position)
    }
}

private class Closure(val name: String?, val params: List<String>, val scope: Scope, val body: Node?, val block: Int) {
    fun callScope(args: List<Any>): Scope {
        val names = HashMap<String, Any>()
        if (name != null) names[name] = this
        params.zip(args).forEach { (param, arg) -> names[param] = arg }
        return Scope(scope, names)
    }

    override fun toString() = if (name == null) "<fn>" else "<fn $name>"
}

private fun checked(value: Long, position: Position): Int {
    if (value < INT_MIN || value > INT_MAX) throw LangError("overflow", position)
    return value.toInt()
}

private fun power(base: Int, exponent: Int, position: Position): Int {
    if ((base == 0 || base == 1) && exponent > 0) return base
    if (base == -1) return if (exponent % 2 == 1) -1 else 1
    var result = 1
    repeat(exponent) { result = checked(result.toLong() * base, position) }
    return result
}

private fun applyBinary(operator: String, left: Any, right: Any, position: Position): Int {
    if (left !is Int || right !is Int) throw LangError("type", position)
    if ((operator == "/" || operator == "%") && right == 0) throw LangError("div-zero", position)
    if (operator == "^" && right < 0) throw LangError("negative-exponent", position)
    val a = left.toLong()
    val b = right.toLong()
    return when (operator) {
        "+" -> checked(a + b, position)
        "-" -> checked(a - b, position)
        "*" -> checked(a * b, position)
        "/" -> checked(a / b, position)
        "%" -> (a % b).toInt()
        "^" -> power(left, right, position)
        "==" -> if (a == b) 1 else 0
        "!=" -> if (a != b) 1 else 0
        "<" -> if (a < b) 1 else 0
        "<=" -> if (a <= b) 1 else 0
        ">" -> if (a > b) 1 else 0
        else -> if (a >= b) 1 else 0
    }
}

private fun negate(value: Any, position: Position): Int {
    if (value !is Int) throw LangError("type", position)
    return checked(-value.toLong(), position)
}

private fun checkCall(callee: Any, count: Int, depth: Int, maxDepth: Int, position: Position): Closure {
    if (callee !is Closure) throw LangError("not-callable", position)
    if (count != callee.params.size) throw LangError("arity", position)
    if (depth >= maxDepth) throw LangError("depth", position)
    return callee
}

private fun truth(value: Any, position: Position): Boolean {
    if (value !is Int) throw LangError("type", position)
    return value != 0
}

private class TreeWalker(private val maxDepth: Int) {
    fun run(node: Node, scope: Scope, depth: Int): Any = when (node) {
        is Num -> node.value
        is Name -> scope.lookup(node.name, node.position)
        is Negate -> negate(run(node.operand, scope, depth), node.position)
        is Binary -> {
            val left = run(node.left, scope, depth)
            val right = run(node.right, scope, depth)
            applyBinary(node.operator, left, right, node.position)
        }
        is If -> run(if (truth(run(node.condition, scope, depth), node.position)) node.then else node.otherwise, scope, depth)
        is Let -> run(node.body, Scope(scope, mapOf(node.name to run(node.value, scope, depth))), depth)
        is Fn -> Closure(node.name, node.params, scope, node.body, node.block)
        is Call -> {
            val callee = run(node.callee, scope, depth)
            val values = node.args.map { run(it, scope, depth) }
            val closure = checkCall(callee, values.size, depth, maxDepth, node.position)
            run(closure.body!!, closure.callScope(values), depth + 1)
        }
    }
}

// ------------------------------------------------------------------------------ level 4: bytecode
private class Instruction(val opcode: String, var operand: Any? = null, val position: Position? = null) {
    fun describe() = listOfNotNull(opcode, operand, position).joinToString(" ")
}

private class Block(val header: String, val name: String?, val params: List<String>) {
    val code = mutableListOf<Instruction>()
}

private class Compiler {
    private val blocks = sortedMapOf<Int, Block>()

    fun program(node: Node): List<Block> {
        blocks[0] = Block("main", null, emptyList())
        emitBlock(0, node)
        return blocks.values.toList()
    }

    private fun emitBlock(number: Int, body: Node) {
        val code = blocks.getValue(number).code
        emit(body, code)
        code.add(Instruction("RETURN"))
    }

    private fun emit(node: Node, code: MutableList<Instruction>) {
        when (node) {
            is Num -> code.add(Instruction("PUSH", node.value))
            is Name -> code.add(Instruction("LOAD", node.name, node.position))
            is Negate -> {
                emit(node.operand, code)
                code.add(Instruction("NEG", null, node.position))
            }
            is Binary -> {
                emit(node.left, code)
                emit(node.right, code)
                code.add(Instruction(OPCODES.getValue(node.operator), null, node.position))
            }
            is If -> {
                emit(node.condition, code)
                val toElse = Instruction("JUMP_IF_ZERO", null, node.position)
                code.add(toElse)
                emit(node.then, code)
                val toEnd = Instruction("JUMP")
                code.add(toEnd)
                toElse.operand = code.size
                emit(node.otherwise, code)
                toEnd.operand = code.size
            }
            is Let -> {
                emit(node.value, code)
                code.add(Instruction("BIND", node.name))
                emit(node.body, code)
                code.add(Instruction("UNBIND"))
            }
            is Fn -> {
                blocks[node.block] = Block(head(node), node.name, node.params)
                emitBlock(node.block, node.body)
                code.add(Instruction("CLOSURE", node.block))
            }
            is Call -> {
                emit(node.callee, code)
                node.args.forEach { emit(it, code) }
                code.add(Instruction("CALL", node.args.size, node.position))
            }
        }
    }
}

private class Frame(val block: Block, var scope: Scope) {
    var ip = 0
}

/**
 * A stack machine: one value stack shared by all frames, and a frame per active call. The loop
 * never recurses, so the depth limit is the only bound on calls.
 */
private fun execute(blocks: List<Block>, maxDepth: Int): Any {
    val stack = ArrayDeque<Any>()
    val frames = ArrayDeque<Frame>()
    frames.addLast(Frame(blocks[0], Scope(null, emptyMap())))
    while (true) {
        val frame = frames.last()
        val instruction = frame.block.code[frame.ip++]
        val position = instruction.position ?: Position(0, 0)
        val operator = OPERATORS[instruction.opcode]
        if (operator != null) {
            val right = stack.removeLast()
            val left = stack.removeLast()
            stack.addLast(applyBinary(operator, left, right, position))
            continue
        }
        when (instruction.opcode) {
            "PUSH" -> stack.addLast(instruction.operand!!)
            "LOAD" -> stack.addLast(frame.scope.lookup(instruction.operand as String, position))
            "NEG" -> stack.addLast(negate(stack.removeLast(), position))
            "JUMP_IF_ZERO" -> if (!truth(stack.removeLast(), position)) frame.ip = instruction.operand as Int
            "JUMP" -> frame.ip = instruction.operand as Int
            "BIND" -> frame.scope = Scope(frame.scope, mapOf(instruction.operand as String to stack.removeLast()))
            "UNBIND" -> frame.scope = frame.scope.parent!!
            "CLOSURE" -> {
                val number = instruction.operand as Int
                val block = blocks[number]
                stack.addLast(Closure(block.name, block.params, frame.scope, null, number))
            }
            "CALL" -> {
                val count = instruction.operand as Int
                val args = List(count) { stack.removeLast() }.asReversed()
                val callee = stack.removeLast()
                val closure = checkCall(callee, count, frames.size - 1, maxDepth, position)
                frames.addLast(Frame(blocks[closure.block], closure.callScope(args)))
            }
            else -> {
                frames.removeLast()
                if (frames.isEmpty()) return stack.removeLast()
            }
        }
    }
}

private fun listing(blocks: List<Block>): List<String> = blocks.flatMapIndexed { number, block ->
    listOf("block $number ${block.header}") + block.code.mapIndexed { index, instruction -> "$index ${instruction.describe()}" }
}

class Interpreter(private val maxDepth: Int) {
    // Level 1
    fun tokenize(source: String): List<String> = try {
        scan(source).map { it.describe() }
    } catch (error: LangError) {
        listOf(error.text())
    }

    // Level 2
    fun parse(source: String): String = try {
        show(parseProgram(source))
    } catch (error: LangError) {
        error.text()
    }

    // Level 3
    fun evaluate(source: String): String = try {
        TreeWalker(maxDepth).run(parseProgram(source), Scope(null, emptyMap()), 0).toString()
    } catch (error: LangError) {
        error.text()
    }

    // Level 4
    fun bytecode(source: String): List<String> = try {
        listing(Compiler().program(parseProgram(source)))
    } catch (error: LangError) {
        listOf(error.text())
    }

    fun run(source: String): String = try {
        execute(Compiler().program(parseProgram(source)), maxDepth).toString()
    } catch (error: LangError) {
        error.text()
    }
}
