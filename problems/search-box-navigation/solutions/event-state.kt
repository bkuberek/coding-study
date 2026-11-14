private const val ARROW_DOWN = "ArrowDown"
private const val ARROW_UP = "ArrowUp"
private const val ENTER = "Enter"
private const val NOTHING = -1

/** The list is empty exactly when nothing is highlighted: [show] keeps the two in step. */
class SearchBox(names: List<String>) {
    private val names = names.toList()
    private val loweredNames = names.map { it.lowercase() }
    private var shown: List<String> = emptyList()
    private var highlight = NOTHING
    private var text = ""
    private var requestsSent = 0
    private var awaitedRequest: Int? = null
    private val selected = mutableListOf<String>()

    // Level 1
    fun keydown(timestamp: Long, key: String) {
        when (key) {
            ARROW_DOWN -> move(1)
            ARROW_UP -> move(-1)
            ENTER -> selectHighlighted()
        }
    }

    /** Releasing a key changes nothing: every action happens when the key goes down. */
    fun keyup(timestamp: Long, key: String) {}

    fun resultsArrived(timestamp: Long, items: List<String>) = show(items)

    fun results(timestamp: Long): List<String> = shown.toList()

    fun highlighted(timestamp: Long): Int = highlight

    fun highlightedText(timestamp: Long): String = if (highlight == NOTHING) "" else shown[highlight]

    // Level 2
    fun search(timestamp: Long, query: String) {
        val needle = query.trim().lowercase()
        if (needle.isEmpty()) {
            show(emptyList())
            return
        }
        show(names.filterIndexed { index, _ -> needle in loweredNames[index] })
    }

    // Level 3
    fun inputChanged(timestamp: Long, text: String): Int {
        this.text = text
        if (text.isBlank()) {
            stopAwaiting()
            return NOTHING
        }
        requestsSent += 1
        awaitedRequest = requestsSent
        return requestsSent
    }

    fun responseArrived(timestamp: Long, requestId: Int, items: List<String>) {
        if (requestId == awaitedRequest) {
            show(items)
        }
    }

    fun inputText(timestamp: Long): String = text

    // Level 4
    fun selections(timestamp: Long): List<String> = selected.toList()

    /** `%` keeps the sign of the dividend; `mod` takes the sign of the divisor. */
    private fun move(step: Int) {
        val count = shown.size
        if (count > 0) {
            highlight = (highlight + step).mod(count)
        }
    }

    private fun selectHighlighted() {
        if (highlight == NOTHING) {
            return
        }
        val choice = shown[highlight]
        selected.add(choice)
        text = choice
        stopAwaiting()
    }

    /** The input changed without a request: no response sent so far may be shown, and the list closes. */
    private fun stopAwaiting() {
        awaitedRequest = null
        show(emptyList())
    }

    private fun show(items: List<String>) {
        shown = items.toList()
        highlight = if (items.isEmpty()) NOTHING else 0
    }
}
