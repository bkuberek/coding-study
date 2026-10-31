package bank

import "testing"

// chain opens a, b and c, then merges c into b and b into a.
func chain(t *testing.T) ledger {
	t.Helper()
	l := newLedger()
	for at, id := range []string{"a", "b", "c"} {
		l.open(int64(at+1), id)
	}
	if !l.merge(10, "b", "c") || !l.merge(20, "a", "b") {
		t.Fatal("merge refused an open pair")
	}
	return l
}

func TestHolderFollowsChainedMerges(t *testing.T) {
	l := chain(t)
	if got := l.holder("c").id; got != "a" {
		t.Errorf(`holder("c") = %q, want "a"`, got)
	}
}

func TestMergedAwayAccountIsNotOpen(t *testing.T) {
	l := chain(t)
	if got := l.findOpen("b"); got != nil {
		t.Errorf(`findOpen("b") = %q, want nil`, got.id)
	}
}

func TestMergedAwayIDIsNeverOpenedAgain(t *testing.T) {
	l := chain(t)
	if l.open(30, "c") {
		t.Error(`open(30, "c") = true, want false`)
	}
}

func TestMergeRefusals(t *testing.T) {
	tests := []struct {
		name        string
		id, otherID string
	}{
		{name: "same account", id: "a", otherID: "a"},
		{name: "missing account", id: "a", otherID: "zed"},
		{name: "merged-away account", id: "a", otherID: "c"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			l := chain(t)
			if l.merge(30, tt.id, tt.otherID) {
				t.Errorf("merge(30, %q, %q) = true, want false", tt.id, tt.otherID)
			}
		})
	}
}

func TestBalanceAtAcrossAMerge(t *testing.T) {
	l := newLedger()
	l.open(1, "kept")
	l.open(2, "other")
	l.find("kept").deposit(3, 10)
	l.find("other").deposit(4, 5)
	l.merge(6, "kept", "other")

	tests := []struct {
		name   string
		id     string
		t      int64
		want   int64
		wantOK bool
	}{
		{name: "kept account before the merge", id: "kept", t: 5, want: 10, wantOK: true},
		{name: "kept account from the merge on", id: "kept", t: 6, want: 15, wantOK: true},
		{name: "merged-away account before the merge", id: "other", t: 5, want: 5, wantOK: true},
		{name: "merged-away account from the merge on", id: "other", t: 6, want: 0, wantOK: false},
		{name: "before the account opened", id: "other", t: 1, want: 0, wantOK: false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got, ok := l.find(tt.id).balanceAt(tt.t); got != tt.want || ok != tt.wantOK {
				t.Errorf("%s.balanceAt(%d) = %d, %v, want %d, %v", tt.id, tt.t, got, ok, tt.want, tt.wantOK)
			}
		})
	}
}
