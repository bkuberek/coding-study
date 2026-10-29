package basic_calculator

import (
	"slices"
	"strings"
)

// levels lists the operators of each precedence level, tightest first.
var levels = []string{"*/", "+-"}

func calculate(s string) int {
	values, operators := tokenize(s)
	for _, level := range levels {
		for {
			position := slices.IndexFunc(operators, func(operator byte) bool {
				return strings.IndexByte(level, operator) >= 0
			})
			if position < 0 {
				break
			}
			values[position] = apply(operators[position], values[position], values[position+1])
			values = slices.Delete(values, position+1, position+2)
			operators = slices.Delete(operators, position, position+1)
		}
	}
	return values[0]
}

// tokenize splits s into numbers and operators; operators[i] joins values[i] and values[i+1].
func tokenize(s string) (values []int, operators []byte) {
	number := 0
	for i := 0; i < len(s); i++ {
		switch character := s[i]; {
		case '0' <= character && character <= '9':
			number = number*10 + int(character-'0')
		case strings.IndexByte("+-*/", character) >= 0:
			values = append(values, number)
			operators = append(operators, character)
			number = 0
		}
	}
	return append(values, number), operators
}

func apply(operator byte, left, right int) int {
	switch operator {
	case '+':
		return left + right
	case '-':
		return left - right
	case '*':
		return left * right
	default:
		return left / right // truncates toward zero
	}
}
