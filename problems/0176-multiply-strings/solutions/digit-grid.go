package multiply_strings

func multiply(num1 string, num2 string) string {
	if num1 == "0" || num2 == "0" {
		return "0"
	}
	// digits[k] is result digit k counted from the left; the product has at most m + n digits.
	digits := make([]int, len(num1)+len(num2))
	for i := len(num1) - 1; i >= 0; i-- {
		carry := 0
		for j := len(num2) - 1; j >= 0; j-- {
			total := digits[i+j+1] + int(num1[i]-'0')*int(num2[j]-'0') + carry
			digits[i+j+1] = total % 10
			carry = total / 10
		}
		digits[i] += carry
	}
	start := 0
	if digits[0] == 0 {
		start = 1 // at most one leading zero
	}
	text := make([]byte, 0, len(digits)-start)
	for _, digit := range digits[start:] {
		text = append(text, byte('0'+digit))
	}
	return string(text)
}
