package evaluate_rpn

import (
	"slices"
	"strconv"
)

// item is one entry of the expression: an operator, or a number when operator is empty.
type item struct {
	operator string
	value    int
}

func evalRPN(tokens []string) int {
	// Operators stay as strings; numbers are parsed once.
	items := make([]item, len(tokens))
	for i, token := range tokens {
		switch token {
		case "+", "-", "*", "/":
			items[i] = item{operator: token}
		default:
			value, _ := strconv.Atoi(token)
			items[i] = item{value: value}
		}
	}
	for len(items) > 1 {
		// The leftmost operator always has its two operands directly in front of it.
		position := slices.IndexFunc(items, func(it item) bool { return it.operator != "" })
		result := apply(items[position].operator, items[position-2].value, items[position-1].value)
		items = slices.Replace(items, position-2, position+1, item{value: result})
	}
	return items[0].value
}

func apply(operator string, left, right int) int {
	switch operator {
	case "+":
		return left + right
	case "-":
		return left - right
	case "*":
		return left * right
	default:
		return left / right // truncates toward zero
	}
}
