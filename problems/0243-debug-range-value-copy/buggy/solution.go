// Debug: Range Value Copy. Some tests fail: find the bug and fix it.
package debug_range_value_copy

type account struct {
	balance int
	expired int
}

func closeMonth(opening []int, earnings [][]int, limit int) [][]int {
	accounts := make([]account, len(opening))
	for i, points := range opening {
		accounts[i].balance = points
	}
	for _, earning := range earnings {
		member, points := earning[0], earning[1]
		accounts[member].balance += points
	}
	for _, acct := range accounts {
		if acct.balance > limit {
			acct.expired = acct.balance - limit
			acct.balance = limit
		}
	}
	statement := make([][]int, len(accounts))
	for i, acct := range accounts {
		statement[i] = []int{acct.balance, acct.expired}
	}
	return statement
}
