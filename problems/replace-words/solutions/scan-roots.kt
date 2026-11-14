class Solution {
    fun replaceWords(dictionary: Array<String>, sentence: String): String =
        sentence.split(' ').joinToString(" ") { word ->
            var best = word
            for (root in dictionary) {
                if (root.length < best.length && word.startsWith(root)) {
                    best = root
                }
            }
            best
        }
}
