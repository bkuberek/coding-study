package runner

import (
	"encoding/json"
	"reflect"
	"testing"
	"time"

	"github.com/shopspring/decimal"
)

const ledgerJob = `{"job_id": "j", "kind": "concurrent", "model": "threads", "target": {"compiled": "user"},
	"names": {"class": "Ledger", "constructor": "NewLedger", "methods": {"add": "Add"}},
	"signature": {"class": {"name": "Ledger", "constructor": {"params": []}, "methods": [
		{"name": "add", "params": [{"name": "value", "type": "decimal"}], "returns": {"type": "decimal"}}]}},
	"cases": [CASES]}`

func TestDecimalAndDateMapToTheVendoredAndStandardTypes(t *testing.T) {
	tests := []struct {
		typeText string
		want     reflect.Type
	}{
		{"decimal", reflect.TypeFor[decimal.Decimal]()},
		{"date", reflect.TypeFor[time.Time]()},
		{"decimal[][]", reflect.TypeFor[[][]decimal.Decimal]()},
		{"list<date>", reflect.TypeFor[[]time.Time]()},
	}
	for _, tt := range tests {
		if got := mustType(t, tt.typeText).goType(); got != tt.want {
			t.Errorf("%s: got %v, want %v", tt.typeText, got, tt.want)
		}
	}
}

func TestDecimalInputsKeepTheirScale(t *testing.T) {
	parsed, err := parseJSON(json.RawMessage(`"2500.00"`))
	if err != nil {
		t.Fatal(err)
	}
	value, err := decode(parsed, mustType(t, "decimal"))
	if err != nil {
		t.Fatal(err)
	}
	if exponent := value.Interface().(decimal.Decimal).Exponent(); exponent != -2 {
		t.Errorf("exponent %d, want -2", exponent)
	}
}

func TestDecimalsEncodeCanonically(t *testing.T) {
	tests := []struct {
		value decimal.Decimal
		want  string
	}{
		{decimal.New(250000, -2), "2500"},
		{decimal.New(0, -3), "0"},
		{decimal.Decimal{}, "0"},
		{decimal.New(-1234, 2), "-123400"},
		{decimal.New(-5, -1), "-0.5"},
		{decimal.New(10100, -3), "10.1"},
		{decimal.New(1, -28), "0.0000000000000000000000000001"},
		{decimal.RequireFromString("-0.0"), "0"},
	}
	for _, tt := range tests {
		if got := canonicalDecimal(tt.value); got != tt.want {
			t.Errorf("%#v: got %s, want %s", tt.value, got, tt.want)
		}
	}
}

func TestDecimalEncodingIgnoresThePackageSettings(t *testing.T) {
	defer freshDecimalSettings()
	decimal.TrimTrailingZeros = false
	decimal.UseScientificNotation = true
	if got := canonicalDecimal(decimal.New(1200, -2)); got != "12" {
		t.Errorf("got %s, want 12", got)
	}
	if got := canonicalDecimal(decimal.New(12, 2)); got != "1200" {
		t.Errorf("got %s, want 1200", got)
	}
}

func TestEveryCaseStartsWithTheDefaultDecimalSettings(t *testing.T) {
	cases := `[{"id": "first", "input": {"value": "1"}}, {"id": "second", "input": {"value": "1"}}]`
	results := named(runJobs(t, function("third", oneParam("third", "decimal", "decimal"), cases)), "case_result")
	for _, result := range results {
		if result["output"] != "0.3333333333333333" {
			t.Errorf("%v: got %v, want 16 places", result["case_id"], result["output"])
		}
	}
}

// Arguments are decoded before the call, so the reset has to come before the decoding.

func TestEveryFunctionCaseDecodesWithTheDefaultDecimalSettings(t *testing.T) {
	cases := `[{"id": "first", "input": {"value": "1"}}, {"id": "second", "input": {"value": "1.50"}}]`
	results := named(runJobs(t, function("strict", oneParam("strict", "decimal", "decimal"), cases)), "case_result")
	for _, result := range results {
		if result["status"] != "ok" || result["output"] == nil {
			t.Errorf("%v: got %v", result["case_id"], result)
		}
	}
}

func TestEveryBenchInputDecodesWithTheDefaultDecimalSettings(t *testing.T) {
	body := `{"protocol": 1, "mode": "bench", "jobs": [{"job_id": "j", "kind": "function",
		"signature": ` + oneParam("strict", "decimal", "decimal") + `,
		"targets": [{"target_id": "user", "target": {"compiled": "user"}, "names": {"function": "strict"}}],
		"inputs": [{"size": 1, "input": {"value": "1"}, "max_batch": 10},
			{"size": 2, "input": {"value": "1.50"}, "max_batch": 10}],
		"settings": {"reps": 3, "warmup": {"min": 1, "max": 3, "cv": 0.05}, "budget_ms": 2000, "memory": false, "min_sample_ns": 1000}}]}`
	_, events := runRequest(t, &loader{registry: registry}, body)
	if errors := named(events, "bench_error"); len(errors) != 0 {
		t.Errorf("got %v", errors)
	}
}

func TestAStressRunDecodesWithTheDefaultDecimalSettings(t *testing.T) {
	job := withCases(ledgerJob,
		`{"id": "ex1", "ops": ["Ledger", "add"], "args": [[], ["1"]]}`,
		stress("s1", "5000", `{"ops": ["Ledger"], "args": [[]]}`,
			[]string{`{"ops": ["add"], "args": [["1.50"]]}`, `{"ops": ["add"], "args": [["1.50"]]}`}, ""))
	results := named(runJobs(t, job), "case_result")
	if len(results) != 2 || results[1]["status"] != "ok" {
		t.Errorf("got %v", results)
	}
}

func TestDatesAreUTCMidnights(t *testing.T) {
	parsed, err := parseJSON(json.RawMessage(`"2024-02-29"`))
	if err != nil {
		t.Fatal(err)
	}
	value, err := decode(parsed, mustType(t, "date"))
	if err != nil {
		t.Fatal(err)
	}
	if day := value.Interface().(time.Time); !day.Equal(time.Date(2024, 2, 29, 0, 0, 0, 0, time.UTC)) || day.Location() != time.UTC {
		t.Errorf("got %v", day)
	}
}

func TestInvalidDecimalAndDateOutputs(t *testing.T) {
	tests := []struct {
		name   string
		value  time.Time
		reason string
	}{
		{"another location", time.Date(2024, 1, 1, 0, 0, 0, 0, time.FixedZone("CET", 3600)), "date must be in time.UTC, got 2024-01-01 00:00:00 in CET"},
		{"not midnight", time.Date(2024, 1, 1, 12, 30, 0, 0, time.UTC), "date must be at midnight, got 2024-01-01T12:30:00Z"},
		{"year 10000", time.Date(10000, 1, 1, 0, 0, 0, 0, time.UTC), "date out of range: 10000-01-01"},
		{"year 0", time.Date(0, 12, 31, 0, 0, 0, 0, time.UTC), "date out of range: 0000-12-31"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := encode(reflect.ValueOf(tt.value), mustType(t, "date"), "")
			if err == nil || err.Error() != tt.reason {
				t.Errorf("got %v, want %q", err, tt.reason)
			}
		})
	}
}

func TestInvalidDecimalAndDateInputs(t *testing.T) {
	tests := []struct {
		typeText string
		input    string
		message  string
	}{
		{"decimal", "1.5", "expected decimal, got 1.5"},
		{"decimal", `"1e5"`, `expected decimal, got "1e5"`},
		{"decimal", `"01.5"`, `expected decimal, got "01.5"`},
		{"decimal", `"1."`, `expected decimal, got "1."`},
		{"decimal", `"+1"`, `expected decimal, got "+1"`},
		{"date", `"2024-1-01"`, `expected date, got "2024-1-01"`},
		{"date", "20240101", "expected date, got 20240101"},
		{"date", `"2023-02-29"`, `"2023-02-29" is not a calendar day`},
		{"date", `"0000-01-01"`, `"0000-01-01" is not a calendar day`},
	}
	for _, tt := range tests {
		t.Run(tt.typeText+" "+tt.input, func(t *testing.T) {
			parsed, err := parseJSON(json.RawMessage(tt.input))
			if err != nil {
				t.Fatal(err)
			}
			_, err = decode(parsed, mustType(t, tt.typeText))
			if err == nil || err.Error() != tt.message {
				t.Errorf("got %v, want %q", err, tt.message)
			}
		})
	}
}
