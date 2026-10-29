package evaluate_rpn

import "strconv"

func evalRPN(tokens []string) int {
	var operands []int
	for _, token := range tokens {
		switch token {
		case "+", "-", "*", "/":
			right := operands[len(operands)-1]
			left := operands[len(operands)-2]
			operands = append(operands[:len(operands)-2], apply(token, left, right))
		default:
			number, _ := strconv.Atoi(token)
			operands = append(operands, number)
		}
	}
	return operands[0]
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
