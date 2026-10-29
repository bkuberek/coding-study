package basic_calculator

import "strings"

func calculate(s string) int {
	total := 0 // the sum of the finished terms
	term := 0  // the signed term still being built
	number := 0
	operator := byte('+') // the operator in front of the number being read
	for i := 0; i < len(s); i++ {
		character := s[i]
		if '0' <= character && character <= '9' {
			number = number*10 + int(character-'0')
		}
		if strings.IndexByte("+-*/", character) >= 0 || i == len(s)-1 {
			switch operator {
			case '+', '-':
				total += term
				term = number
				if operator == '-' {
					term = -number
				}
			case '*':
				term *= number
			default:
				term /= number // truncates toward zero
			}
			operator = character
			number = 0
		}
	}
	return total + term
}
