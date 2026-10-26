class Solution {
    fun calculate(s: String): Int {
        var total = 0 // the sum of the finished terms
        var term = 0 // the signed term still being built
        var number = 0
        var operator = '+' // the operator in front of the number being read
        for ((i, character) in s.withIndex()) {
            if (character.isDigit()) {
                number = number * 10 + (character - '0')
            }
            if (character in "+-*/" || i == s.lastIndex) {
                when (operator) {
                    '+', '-' -> {
                        total += term
                        term = if (operator == '+') number else -number
                    }
                    '*' -> term *= number
                    else -> term /= number // truncates toward zero
                }
                operator = character
                number = 0
            }
        }
        return total + term
    }
}
