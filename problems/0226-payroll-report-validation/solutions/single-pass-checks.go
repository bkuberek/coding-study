package payroll_report_validation

import (
	"regexp"
	"strconv"
	"time"

	"github.com/shopspring/decimal"
)

var fields = [...]string{"contractorId", "classCode", "payroll", "periodStart"}

var (
	contractorID = regexp.MustCompile(`^[a-z0-9-]{1,20}$`)
	classCode    = regexp.MustCompile(`^[0-9]{4}$`)
	payrollShape = regexp.MustCompile(`^[0-9]+(\.[0-9]{1,2})?$`)
	isoDay       = regexp.MustCompile(`^[0-9]{4}-[0-9]{2}-[0-9]{2}$`)
)

var (
	maxPayroll = decimal.NewFromInt(1_000_000_000)
	firstDay   = time.Date(2000, 1, 1, 0, 0, 0, 0, time.UTC)
	lastDay    = time.Date(2099, 12, 31, 0, 0, 0, 0, time.UTC)
)

func validateRows(rows [][]string) []string {
	errors := []string{}
	type key struct{ contractorID, classCode, periodStart string }
	seenKeys := make(map[key]struct{})
	for index, row := range rows {
		if len(row) != len(fields) {
			errors = append(errors, strconv.Itoa(index)+":row:column-count")
			continue
		}
		reasons := [...]string{
			checkPattern(row[0], contractorID),
			checkPattern(row[1], classCode),
			checkPayroll(row[2]),
			checkPeriodStart(row[3]),
		}
		for i, reason := range reasons {
			if reason != "" {
				errors = append(errors, strconv.Itoa(index)+":"+fields[i]+":"+reason)
			}
		}
		if reasons[0] == "" && reasons[1] == "" && reasons[3] == "" {
			k := key{row[0], row[1], row[3]}
			if _, duplicate := seenKeys[k]; duplicate {
				errors = append(errors, strconv.Itoa(index)+":row:duplicate")
			}
			seenKeys[k] = struct{}{}
		}
	}
	return errors
}

func checkPattern(value string, pattern *regexp.Regexp) string {
	if value == "" {
		return "missing"
	}
	if pattern.MatchString(value) {
		return ""
	}
	return "invalid"
}

func checkPayroll(value string) string {
	if reason := checkPattern(value, payrollShape); reason != "" {
		return reason
	}
	amount, err := decimal.NewFromString(value)
	if err != nil || !amount.IsPositive() || amount.GreaterThan(maxPayroll) {
		return "out-of-range"
	}
	return ""
}

func checkPeriodStart(value string) string {
	if reason := checkPattern(value, isoDay); reason != "" {
		return reason
	}
	day, err := time.Parse(time.DateOnly, value)
	if err != nil || day.Year() < 1 { // time.Parse accepts year 0, which is not a real year here
		return "invalid"
	}
	if day.Before(firstDay) || day.After(lastDay) {
		return "out-of-range"
	}
	return ""
}
