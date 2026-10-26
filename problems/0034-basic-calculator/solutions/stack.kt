class Solution {
    fun calculate(s: String): Int {
        val terms = ArrayDeque<Int>() // signed terms; the last one may still change
        var number = 0
        var operator = '+' // the operator in front of the number being read
        for ((i, character) in s.withIndex()) {
            if (character.isDigit()) {
                number = number * 10 + (character - '0')
            }
            if (character in "+-*/" || i == s.lastIndex) {
                when (operator) {
                    '+' -> terms.addLast(number)
                    '-' -> terms.addLast(-number)
                    '*' -> terms.addLast(terms.removeLast() * number)
                    else -> terms.addLast(terms.removeLast() / number) // truncates toward zero
                }
                operator = character
                number = 0
            }
        }
        return terms.sum()
    }
}
