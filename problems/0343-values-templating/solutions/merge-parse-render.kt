/**
 * Layers are kept as given and merged on demand, oldest first, with the rules of RFC 7396. Every
 * node of the merged tree remembers the layer that set it. A template is parsed in one
 * left-to-right pass into a tree of text, substitutions, conditionals and loops, and rendered with
 * a stack of loop bindings that shadow the values.
 */
class ValuesRenderer {
    private class Node(val kind: String, val text: String = "", val layer: String = "") {
        val members = HashMap<String, Node>()
        val items = ArrayList<Node>()

        fun copy(newLayer: String): Node {
            val twin = Node(kind, text, newLayer)
            for ((key, child) in members) twin.members[key] = child.copy(newLayer)
            for (child in items) twin.items.add(child.copy(newLayer))
            return twin
        }
    }

    private class TemplateError(val code: String, val position: Int, val detail: String = "") : RuntimeException(code)

    private data class Token(val kind: String, val value: String)

    private sealed interface Tag {
        data class Text(val text: String) : Tag
        data class Out(val path: String, val fallback: String?) : Tag
        data class If(val path: String) : Tag
        object Else : Tag
        object End : Tag
        data class For(val names: List<String>, val path: String) : Tag
    }

    private class Segment(val text: String?, val tag: Tag?, val at: Int, val trimLeft: Boolean, val trimRight: Boolean)

    private sealed interface Part {
        class Text(val text: String) : Part
        class Out(val path: String, val fallback: String?, val at: Int) : Part
        class If(val path: String, val at: Int) : Part {
            val then = ArrayList<Part>()
            val otherwise = ArrayList<Part>()
        }
        class For(val names: List<String>, val path: String, val at: Int) : Part {
            val body = ArrayList<Part>()
        }
    }

    private class Open(val isIf: Boolean, val at: Int, var hasElse: Boolean = false)

    private val layers = LinkedHashMap<String, Node>()
    private var schema = Node("object")

    // Level 1
    fun setLayer(name: String, rows: List<List<String>>): Boolean {
        val isNew = name !in layers
        layers[name] = decode(rows)
        return isNew
    }

    fun merged(): List<List<String>> {
        val rows = ArrayList<List<String>>()
        walk(merge(), "") { pointer, node -> rows.add(listOf(pointer, node.kind, node.text)) }
        return rows
    }

    // Level 2 and 3
    fun render(template: String): List<String> {
        val values = merge()
        val errors = errors(values)
        if (errors.isNotEmpty()) return listOf("error", "invalid_values", "", errors.size.toString())
        return try {
            val out = StringBuilder()
            emit(parse(template), values, emptyList(), out)
            listOf("ok", out.toString())
        } catch (error: TemplateError) {
            listOf("error", error.code, lineAndColumn(template, error.position), error.detail)
        }
    }

    // Level 4
    fun setSchema(rows: List<List<String>>) {
        schema = decode(rows)
    }

    fun validate(): List<List<String>> = errors(merge())

    fun provenance(): List<List<String>> {
        val rows = ArrayList<List<String>>()
        walk(merge(), "") { pointer, node -> rows.add(listOf(pointer, node.layer)) }
        return rows
    }

    // Merging
    private fun merge(): Node {
        val root = Node("object")
        for ((name, layer) in layers) mergeInto(root, layer, name)
        return root
    }

    private fun decode(rows: List<List<String>>): Node {
        val root = Node("object")
        for ((pointer, kind, text) in rows) {
            val segments = pointer.substring(1).split("/")
            var parent = root
            for (segment in segments.dropLast(1)) {
                parent = if (parent.kind == "object") parent.members.getValue(segment) else parent.items[segment.toInt()]
            }
            val node = Node(kind, text)
            if (parent.kind == "object") parent.members[segments.last()] = node else parent.items.add(node)
        }
        return root
    }

    private fun walk(node: Node, pointer: String, visit: (String, Node) -> Unit) {
        if (node.kind == "object") {
            for (key in node.members.keys.sorted()) {
                val child = node.members.getValue(key)
                visit("$pointer/$key", child)
                walk(child, "$pointer/$key", visit)
            }
        } else if (node.kind == "array") {
            node.items.forEachIndexed { index, child ->
                visit("$pointer/$index", child)
                walk(child, "$pointer/$index", visit)
            }
        }
    }

    private fun mergeInto(target: Node, patch: Node, layer: String) {
        for ((key, value) in patch.members) {
            when (value.kind) {
                "null" -> target.members.remove(key)
                "object" -> {
                    var current = target.members[key]
                    if (current == null || current.kind != "object") {
                        current = Node("object", "", layer)
                        target.members[key] = current
                    }
                    mergeInto(current, value, layer)
                }
                else -> target.members[key] = value.copy(layer)
            }
        }
    }

    // Parsing
    private fun isWordChar(c: Char): Boolean = c in 'a'..'z' || c in 'A'..'Z' || c in '0'..'9' || c == '_' || c == '.'

    private fun tokenize(body: String, position: Int): List<Token> {
        val tokens = ArrayList<Token>()
        var i = 0
        while (i < body.length) {
            val c = body[i]
            when {
                c == ' ' -> i++
                c == '|' || c == ',' -> {
                    tokens.add(Token("punct", c.toString()))
                    i++
                }
                c == '"' -> {
                    val text = StringBuilder()
                    i++
                    while (true) {
                        if (i >= body.length) throw TemplateError("bad_expression", position)
                        val d = body[i]
                        if (d == '"') break
                        if (d == '\\') {
                            val next = body.getOrNull(i + 1)
                            if (next != '"' && next != '\\') throw TemplateError("bad_expression", position)
                            text.append(next)
                            i += 2
                        } else {
                            text.append(d)
                            i++
                        }
                    }
                    tokens.add(Token("string", text.toString()))
                    i++
                }
                isWordChar(c) -> {
                    val start = i
                    while (i < body.length && isWordChar(body[i])) i++
                    tokens.add(Token("word", body.substring(start, i)))
                }
                else -> throw TemplateError("bad_expression", position)
            }
        }
        return tokens
    }

    private fun classify(tokens: List<Token>, position: Int): Tag {
        val kinds = tokens.map { it.kind }
        val words = tokens.map { it.value }
        if (tokens.isNotEmpty() && kinds[0] == "word" && words[0] in BLOCK_WORDS) return classifyBlock(kinds, words, position)
        if (kinds == listOf("string")) return Tag.Text(words[0])
        if (kinds == listOf("word") && PATH.matches(words[0])) return Tag.Out(words[0], null)
        if (kinds == listOf("word", "punct", "word", "string") && PATH.matches(words[0]) &&
            words[1] == "|" && words[2] == "default"
        ) {
            return Tag.Out(words[0], words[3])
        }
        throw TemplateError("bad_expression", position)
    }

    private fun classifyBlock(kinds: List<String>, words: List<String>, position: Int): Tag {
        val head = words[0]
        if (head == "else" && words.size == 1) return Tag.Else
        if (head == "end" && words.size == 1) return Tag.End
        if (head == "if" && kinds == listOf("word", "word") && PATH.matches(words[1])) return Tag.If(words[1])
        if (head == "for") {
            val names = when {
                kinds == listOf("word", "word", "word", "word") && words[2] == "in" -> listOf(words[1])
                kinds == listOf("word", "word", "punct", "word", "word", "word") && words[2] == "," && words[4] == "in" ->
                    listOf(words[1], words[3])
                else -> emptyList()
            }
            val valid = names.all { KEY.matches(it) && it !in RESERVED }
            if (names.isNotEmpty() && valid && names.toSet().size == names.size && PATH.matches(words.last())) {
                return Tag.For(names, words.last())
            }
        }
        throw TemplateError("bad_expression", position)
    }

    private fun parse(template: String): List<Part> {
        val segments = ArrayList<Segment>()
        val stack = ArrayList<Open>()
        var i = 0
        while (true) {
            val start = template.indexOf("{{", i)
            if (start < 0) {
                segments.add(Segment(template.substring(i), null, 0, false, false))
                break
            }
            segments.add(Segment(template.substring(i, start), null, 0, false, false))
            val end = template.indexOf("}}", start + 2)
            if (end < 0) throw TemplateError("unclosed_tag", start)
            var body = template.substring(start + 2, end)
            val trimLeft = body.startsWith("-")
            if (trimLeft) body = body.substring(1)
            val trimRight = body.endsWith("-")
            if (trimRight) body = body.dropLast(1)
            val tag = classify(tokenize(body.trim(' '), start), start)
            when (tag) {
                is Tag.If -> stack.add(Open(true, start))
                is Tag.For -> stack.add(Open(false, start))
                Tag.Else -> {
                    val top = stack.lastOrNull()
                    if (top == null || !top.isIf || top.hasElse) throw TemplateError("unexpected_tag", start)
                    top.hasElse = true
                }
                Tag.End -> {
                    if (stack.isEmpty()) throw TemplateError("unexpected_tag", start)
                    stack.removeAt(stack.size - 1)
                }
                else -> {}
            }
            segments.add(Segment(null, tag, start, trimLeft, trimRight))
            i = end + 2
        }
        if (stack.isNotEmpty()) throw TemplateError("unclosed_block", stack.last().at)
        for (k in segments.indices) {
            val segment = segments[k]
            if (segment.tag == null) continue
            if (segment.trimLeft) segments[k - 1] = Segment(segments[k - 1].text!!.trimEnd(' ', '\n'), null, 0, false, false)
            if (segment.trimRight) segments[k + 1] = Segment(segments[k + 1].text!!.trimStart(' ', '\n'), null, 0, false, false)
        }
        return build(segments)
    }

    private fun build(segments: List<Segment>): List<Part> {
        val root = ArrayList<Part>()
        val blocks = ArrayList<Part>()
        val outers = ArrayList<MutableList<Part>>()
        var current: MutableList<Part> = root
        for (segment in segments) {
            val tag = segment.tag
            if (tag == null) {
                if (segment.text!!.isNotEmpty()) current.add(Part.Text(segment.text))
                continue
            }
            when (tag) {
                is Tag.If -> {
                    val block = Part.If(tag.path, segment.at)
                    current.add(block)
                    blocks.add(block)
                    outers.add(current)
                    current = block.then
                }
                is Tag.For -> {
                    val block = Part.For(tag.names, tag.path, segment.at)
                    current.add(block)
                    blocks.add(block)
                    outers.add(current)
                    current = block.body
                }
                Tag.Else -> current = (blocks.last() as Part.If).otherwise
                Tag.End -> {
                    blocks.removeAt(blocks.size - 1)
                    current = outers.removeAt(outers.size - 1)
                }
                is Tag.Text -> current.add(Part.Text(tag.text))
                is Tag.Out -> current.add(Part.Out(tag.path, tag.fallback, segment.at))
            }
        }
        return root
    }

    private fun lineAndColumn(template: String, position: Int): String {
        val before = template.substring(0, position)
        val line = before.count { it == '\n' } + 1
        val column = position - (before.lastIndexOf('\n') + 1) + 1
        return "$line:$column"
    }

    // Rendering
    private fun emit(parts: List<Part>, values: Node, scope: List<Pair<String, Node>>, out: StringBuilder) {
        for (part in parts) {
            when (part) {
                is Part.Text -> out.append(part.text)
                is Part.Out -> {
                    val found = lookup(part.path, values, scope)
                    when {
                        found == null -> out.append(part.fallback ?: throw TemplateError("missing_value", part.at, part.path))
                        found.kind == "object" || found.kind == "array" -> throw TemplateError("not_scalar", part.at, part.path)
                        else -> out.append(found.text)
                    }
                }
                is Part.If -> emit(if (truthy(lookup(part.path, values, scope))) part.then else part.otherwise, values, scope, out)
                is Part.For -> loop(part, values, scope, out)
            }
        }
    }

    private fun loop(part: Part.For, values: Node, scope: List<Pair<String, Node>>, out: StringBuilder) {
        val found = lookup(part.path, values, scope) ?: throw TemplateError("missing_value", part.at, part.path)
        val pairs = when (found.kind) {
            "array" -> found.items.mapIndexed { index, item -> Node("number", index.toString()) to item }
            "object" -> found.members.keys.sorted().map { key -> Node("string", key) to found.members.getValue(key) }
            else -> throw TemplateError("not_iterable", part.at, part.path)
        }
        for ((key, item) in pairs) {
            val bound = if (part.names.size == 2) listOf(part.names[0] to key, part.names[1] to item) else listOf(part.names[0] to item)
            emit(part.body, values, scope + bound, out)
        }
    }

    private fun lookup(path: String, values: Node, scope: List<Pair<String, Node>>): Node? {
        var segments = path.split(".")
        var current: Node? = values
        val binding = scope.lastOrNull { it.first == segments[0] }
        if (binding != null) {
            current = binding.second
            segments = segments.drop(1)
        }
        for (segment in segments) {
            val node = current ?: return null
            current = when {
                node.kind == "object" -> node.members[segment]
                node.kind == "array" && INDEX.matches(segment) -> node.items.getOrNull(segment.toIntOrNull() ?: Int.MAX_VALUE)
                else -> return null
            }
        }
        return if (current == null || current.kind == "null") null else current
    }

    private fun truthy(node: Node?): Boolean = when {
        node == null -> false
        node.kind == "boolean" -> node.text == "true"
        node.kind == "string" -> node.text.isNotEmpty()
        node.kind == "number" -> node.text != "0"
        node.kind == "object" -> node.members.isNotEmpty()
        else -> node.items.isNotEmpty()
    }

    // Validation
    private fun errors(values: Node): List<List<String>> {
        val errors = ArrayList<List<String>>()
        check(values, schema, "", errors)
        return errors.sortedWith(compareBy<List<String>>({ it[0] }, { it[1] }))
    }

    private fun hasType(node: Node, name: String): Boolean = node.kind == name || (name == "integer" && node.kind == "number")

    private fun isListed(node: Node, options: Node): Boolean =
        node.kind != "object" && node.kind != "array" && options.items.any { it.kind == node.kind && it.text == node.text }

    private fun check(node: Node, schema: Node, pointer: String, errors: MutableList<List<String>>) {
        val keywords = schema.members
        keywords["type"]?.let { if (!hasType(node, it.text)) errors.add(listOf(pointer, "type", node.layer)) }
        keywords["enum"]?.let { if (!isListed(node, it)) errors.add(listOf(pointer, "enum", node.layer)) }
        if (node.kind == "number") {
            val value = node.text.toLong()
            keywords["minimum"]?.let { if (value < it.text.toLong()) errors.add(listOf(pointer, "minimum", node.layer)) }
            keywords["maximum"]?.let { if (value > it.text.toLong()) errors.add(listOf(pointer, "maximum", node.layer)) }
        }
        if (node.kind == "object") {
            val properties = keywords["properties"]?.members ?: emptyMap()
            for (key in keywords["required"]?.items ?: emptyList()) {
                if (key.text !in node.members) errors.add(listOf("$pointer/${key.text}", "required", ""))
            }
            val closed = keywords["additionalProperties"]?.text == "false"
            for ((key, child) in node.members) {
                val sub = properties[key]
                if (sub != null) {
                    check(child, sub, "$pointer/$key", errors)
                } else if (closed) {
                    errors.add(listOf("$pointer/$key", "additionalProperties", child.layer))
                }
            }
        }
        val items = keywords["items"]
        if (node.kind == "array" && items != null) {
            node.items.forEachIndexed { index, child -> check(child, items, "$pointer/$index", errors) }
        }
    }

    private companion object {
        val KEY = Regex("[A-Za-z_][A-Za-z0-9_]*")
        val INDEX = Regex("0|[1-9][0-9]*")
        const val SEGMENT = "(?:[A-Za-z_][A-Za-z0-9_]*|0|[1-9][0-9]*)"
        val PATH = Regex("$SEGMENT(?:\\.$SEGMENT)*")
        val BLOCK_WORDS = setOf("if", "else", "end", "for")
        val RESERVED = setOf("if", "else", "end", "for", "in")
    }
}
