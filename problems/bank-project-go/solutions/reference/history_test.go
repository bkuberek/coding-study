package bank

import "testing"

func TestHistoryAt(t *testing.T) {
	var h history
	h.record(10, 0)
	h.record(20, 5)
	h.record(20, 8)
	h.record(30, 2)

	tests := []struct {
		name   string
		t      int64
		want   int64
		wantOK bool
	}{
		{name: "before the first change", t: 9, want: 0, wantOK: false},
		{name: "at the first change", t: 10, want: 0, wantOK: true},
		{name: "between changes", t: 19, want: 0, wantOK: true},
		{name: "several changes at one moment answer with the last", t: 20, want: 8, wantOK: true},
		{name: "after the last change", t: 99, want: 2, wantOK: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got, ok := h.at(tt.t); got != tt.want || ok != tt.wantOK {
				t.Errorf("at(%d) = %d, %v, want %d, %v", tt.t, got, ok, tt.want, tt.wantOK)
			}
		})
	}
}
