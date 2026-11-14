package main

import (
	"regexp"
	"time"
)

// dayForm is the one form a day takes in this API, in ASCII digits.
var dayForm = regexp.MustCompile(`^[0-9]{4}-[0-9]{2}-[0-9]{2}$`)

// parseDay is the day text names, written YYYY-MM-DD, and false when it names no real day. The
// form is checked first, since time.Parse also takes a year with a sign.
func parseDay(text string) (time.Time, bool) {
	if !dayForm.MatchString(text) {
		return time.Time{}, false
	}
	day, err := time.Parse(time.DateOnly, text)
	return day, err == nil
}
