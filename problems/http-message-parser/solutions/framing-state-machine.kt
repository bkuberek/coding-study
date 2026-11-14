private const val CRLF = "\r\n"
private const val END_OF_HEAD = "\r\n\r\n"
private const val TOKEN_SYMBOLS = "!#$%&'*+-.^_`|~"

// A size with more significant digits than this is larger than any limit, so it is never
// converted into a number: that is how a size such as 10000000000000000 (hex) cannot wrap.
private const val MAX_SIGNIFICANT_DIGITS = 12
private const val TOO_MANY_DIGITS = 1L shl 62

private class Failure(val code: String) : Exception(code)

private class NeedMore : Exception()

private class Message(val rows: MutableList<List<String>>, val end: Int)

private fun Char.isTokenChar() = this in '0'..'9' || this in 'a'..'z' || this in 'A'..'Z' || this in TOKEN_SYMBOLS

private fun isToken(text: String) = text.isNotEmpty() && text.all { it.isTokenChar() }

private fun Char.isHexDigit() = this in '0'..'9' || this in 'a'..'f' || this in 'A'..'F'

private fun trimOws(text: String) = text.trim(' ', '\t')

/** The value of a run of digits, or a huge number when it has too many digits to matter. */
private fun sizeOf(digits: String, radix: Int): Long {
    val significant = digits.trimStart('0')
    return when {
        significant.isEmpty() -> 0L
        significant.length > MAX_SIGNIFICANT_DIGITS -> TOO_MANY_DIGITS
        else -> significant.toLong(radix)
    }
}

private fun skipEmptyLines(data: String, start: Int): Int {
    var pos = start
    while (data.startsWith(CRLF, pos)) pos += 2
    return pos
}

private fun checkLineEndings(text: String) {
    val rest = text.replace(CRLF, "")
    if ('\r' in rest || '\n' in rest) throw Failure("bad-line-ending")
}

private fun parseRequestLine(line: String): List<String> {
    val parts = line.split(" ")
    if (parts.size != 3) throw Failure("bad-request-line")
    val (method, target, version) = parts
    val validTarget = target.isNotEmpty() && target.all { it in '!'..'~' }
    val validVersion = version.length == 8 && version.startsWith("HTTP/") &&
        version[5] in '0'..'9' && version[6] == '.' && version[7] in '0'..'9'
    if (!isToken(method) || !validTarget || !validVersion) throw Failure("bad-request-line")
    return listOf("request", method, target, version)
}

private fun parseFieldLine(tag: String, line: String): List<String> {
    if (line.startsWith(" ") || line.startsWith("\t")) throw Failure("obs-fold")
    val colon = line.indexOf(':')
    if (colon == -1 || !isToken(line.substring(0, colon))) throw Failure("bad-field")
    val value = trimOws(line.substring(colon + 1))
    if (!value.all { it == '\t' || it in ' '..'~' }) throw Failure("bad-field")
    return listOf(tag, line.substring(0, colon).lowercase(), value)
}

/** A comma-separated list over every field line, with empty elements dropped. */
private fun listElements(values: List<String>): List<String> =
    values.joinToString(",").split(",").map(::trimOws).filter { it.isNotEmpty() }

/**
 * A request is read in three stages: skip empty lines, find the end of the head (the first CRLF
 * CRLF), then read the body that the framing fields announce. Each stage either finishes, needs
 * more bytes, or fails, and the same code serves the one-shot methods and the connection: `feed`
 * keeps the unread bytes and runs the stages again each time more arrive, so a message is
 * reported by the call that completes it.
 */
class HttpParser {
    private var headLimit: Long? = null
    private var bodyLimit: Long? = null
    private var buffer = ""
    private var closed = false

    // Level 1
    fun parseHead(data: String): List<List<String>> = reporting {
        val start = skipEmptyLines(data, 0)
        val end = endOfHead(data, start)
        headRows(data.substring(start, end - 4))
    }

    // Level 2
    fun parseMessage(data: String): List<List<String>> = reporting {
        message(data, skipEmptyLines(data, 0)).rows
    }

    // Level 3
    fun feed(data: String): List<List<String>> {
        if (closed) return emptyList()
        buffer += data
        val rows = mutableListOf<List<String>>()
        while (true) {
            buffer = buffer.substring(skipEmptyLines(buffer, 0))
            val message = try {
                message(buffer, 0)
            } catch (needMore: NeedMore) {
                return rows
            } catch (failure: Failure) {
                closed = true
                buffer = ""
                rows.add(listOf("error", failure.code))
                return rows
            }
            rows.addAll(message.rows)
            buffer = buffer.substring(message.end)
        }
    }

    fun close(): List<List<String>> {
        if (closed) return emptyList()
        closed = true
        return if (buffer.isEmpty()) emptyList() else listOf(listOf("error", "incomplete"))
    }

    // Level 4
    fun setLimits(maxHeadBytes: Int, maxBodyBytes: Int) {
        headLimit = maxHeadBytes.toLong()
        bodyLimit = maxBodyBytes.toLong()
    }

    // The stages
    private fun reporting(parse: () -> List<List<String>>): List<List<String>> = try {
        parse()
    } catch (needMore: NeedMore) {
        listOf(listOf("error", "incomplete"))
    } catch (failure: Failure) {
        listOf(listOf("error", failure.code))
    }

    /**
     * The index just after the head's empty line. With a limit, only the first `limit` bytes are
     * searched, so a head that cannot fit fails without waiting.
     */
    private fun endOfHead(data: String, start: Int): Int {
        val limit = headLimit
        val found = if (limit == null) {
            data.indexOf(END_OF_HEAD, start)
        } else {
            val window = data.substring(start, minOf(data.length.toLong(), start + limit).toInt())
            val inWindow = window.indexOf(END_OF_HEAD)
            if (inWindow == -1 && data.length - start >= limit) throw Failure("head-too-large")
            if (inWindow == -1) -1 else start + inWindow
        }
        if (found == -1) throw NeedMore()
        return found + 4
    }

    private fun headRows(text: String): MutableList<List<String>> {
        checkLineEndings(text)
        val lines = text.split(CRLF)
        val request = parseRequestLine(lines[0])
        val rows = mutableListOf(request)
        lines.drop(1).mapTo(rows) { parseFieldLine("field", it) }
        val hosts = rows.drop(1).count { it[1] == "host" }
        if (hosts > 1 || (hosts == 0 && request[3] == "HTTP/1.1")) throw Failure("bad-host")
        return rows
    }

    private fun message(data: String, start: Int): Message {
        val headEnd = endOfHead(data, start)
        val rows = headRows(data.substring(start, headEnd - 4))
        val fields = rows.drop(1)
        val codings = fields.filter { it[1] == "transfer-encoding" }.map { it[2] }
        val lengths = fields.filter { it[1] == "content-length" }.map { it[2] }
        if (codings.isNotEmpty() && lengths.isNotEmpty()) throw Failure("ambiguous-length")
        if (codings.isNotEmpty()) {
            val list = listElements(codings)
            if (list.size != 1 || !list[0].equals("chunked", ignoreCase = true)) {
                throw Failure("unsupported-transfer-coding")
            }
            return chunked(data, headEnd, rows)
        }
        val length = if (lengths.isEmpty()) 0L else contentLength(lengths)
        if (data.length - headEnd < length) throw NeedMore()
        val end = headEnd + length.toInt()
        rows.add(listOf("body", data.substring(headEnd, end)))
        return Message(rows, end)
    }

    private fun contentLength(lines: List<String>): Long {
        val elements = listElements(lines)
        if (elements.isEmpty() || !elements.all { element -> element.all { it in '0'..'9' } }) {
            throw Failure("bad-content-length")
        }
        if (elements.map { it.trimStart('0') }.toSet().size > 1) {
            throw Failure("conflicting-content-length")
        }
        val length = sizeOf(elements[0], 10)
        if (tooLarge(length, 0)) throw Failure("body-too-large")
        return length
    }

    private fun tooLarge(size: Long, used: Long): Boolean {
        val limit = bodyLimit ?: return false
        return used + size > limit
    }

    private fun chunked(data: String, start: Int, rows: MutableList<List<String>>): Message {
        var pos = start
        val content = StringBuilder()
        var total = 0L
        while (true) {
            val lineEnd = data.indexOf(CRLF, pos)
            if (lineEnd == -1) throw NeedMore()
            val size = chunkSize(data.substring(pos, lineEnd))
            if (tooLarge(size, total)) throw Failure("body-too-large")
            pos = lineEnd + 2
            if (size == 0L) break
            if (data.length - pos < size + 2) throw NeedMore()
            val end = pos + size.toInt()
            if (!data.startsWith(CRLF, end)) throw Failure("bad-chunk")
            content.append(data, pos, end)
            total += size
            pos = end + 2
        }
        rows.add(listOf("body", content.toString()))
        if (data.startsWith(CRLF, pos)) return Message(rows, pos + 2)
        val found = data.indexOf(END_OF_HEAD, pos)
        if (found == -1) throw NeedMore()
        val text = data.substring(pos, found)
        checkLineEndings(text)
        text.split(CRLF).mapTo(rows) { parseFieldLine("trailer", it) }
        return Message(rows, found + 4)
    }

    private fun chunkSize(line: String): Long {
        if ('\r' in line || '\n' in line) throw Failure("bad-chunk-size")
        val semicolon = line.indexOf(';')
        val digits = if (semicolon == -1) line else line.substring(0, semicolon).trimEnd(' ', '\t')
        if (digits.isEmpty() || !digits.all { it.isHexDigit() }) throw Failure("bad-chunk-size")
        return sizeOf(digits, 16)
    }
}
