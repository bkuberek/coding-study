package basic_calculator

import "strings"

func calculate(s string) int {
	var terms []int // signed terms; the last one may still be multiplied or divided
	number := 0
	operator := byte('+') // the operator in front of the number being read
	for i := 0; i < len(s); i++ {
		character := s[i]
		if '0' <= character && character <= '9' {
			number = number*10 + int(character-'0')
		}
		if strings.IndexByte("+-*/", character) >= 0 || i == len(s)-1 {
			last := len(terms) - 1
			switch operator {
			case '+':
				terms = append(terms, number)
			case '-':
				terms = append(terms, -number)
			case '*':
				terms[last] *= number
			default:
				terms[last] /= number // truncates toward zero
			}
			operator = character
			number = 0
		}
	}
	total := 0
	for _, term := range terms {
		total += term
	}
	return total
}
