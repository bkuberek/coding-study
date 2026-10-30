package valid_parenthesis_string

func checkValidString(s string) bool {
	var opens []int // positions of unmatched "("
	var stars []int // positions of unused "*"
	for position := 0; position < len(s); position++ {
		switch {
		case s[position] == '(':
			opens = append(opens, position)
		case s[position] == '*':
			stars = append(stars, position)
		case len(opens) > 0:
			opens = opens[:len(opens)-1] // prefer a real "(" and keep wildcards for later
		case len(stars) > 0:
			stars = stars[:len(stars)-1]
		default:
			return false
		}
	}
	// Every remaining "(" needs a later "*" to act as its ")".
	for len(opens) > 0 && len(stars) > 0 {
		open, star := opens[len(opens)-1], stars[len(stars)-1]
		opens, stars = opens[:len(opens)-1], stars[:len(stars)-1]
		if open > star {
			return false
		}
	}
	return len(opens) == 0
}
