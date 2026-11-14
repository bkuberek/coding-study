package main

import "testing"

func TestADayIsRealOnlyInTheFormOfThisAPI(t *testing.T) {
	days := map[string]bool{
		"2027-03-01":   true,
		"2028-02-29":   true,
		"2027-02-29":   false,
		"2027-02-30":   false,
		"2027-13-01":   false,
		"2027-3-1":     false,
		"soon":         false,
		"-027-03-01":   false,
		"+12027-03-01": false,
		"2027-03-01\n": false,
		"２０２７-03-01":   false,
	}
	for text, want := range days {
		if _, found := parseDay(text); found != want {
			t.Errorf("parseDay(%q) says %v, want %v", text, found, want)
		}
	}
}
