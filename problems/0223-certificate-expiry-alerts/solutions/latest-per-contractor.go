package certificate_expiry_alerts

import (
	"slices"
	"strings"
	"time"
)

type certificate struct {
	contractorID string
	expiry       time.Time
}

func certificateAlerts(contractorIds []string, expiryDates []time.Time, asOfDate time.Time, windowDays int) [][]string {
	latest := make(map[string]time.Time) // a renewal supersedes: only the latest expiry counts
	for i, id := range contractorIds {
		if current, seen := latest[id]; !seen || expiryDates[i].After(current) {
			latest[id] = expiryDates[i]
		}
	}
	horizon := asOfDate.AddDate(0, 0, windowDays)
	flagged := make([]certificate, 0, len(latest))
	for id, expiry := range latest {
		if !expiry.After(horizon) {
			flagged = append(flagged, certificate{contractorID: id, expiry: expiry})
		}
	}
	// By date, then by id in byte order (the ids are ASCII, so that is code point order).
	slices.SortFunc(flagged, func(a, b certificate) int {
		if byDate := a.expiry.Compare(b.expiry); byDate != 0 {
			return byDate
		}
		return strings.Compare(a.contractorID, b.contractorID)
	})
	rows := make([][]string, len(flagged))
	for i, cert := range flagged {
		status := "expired"
		if cert.expiry.After(asOfDate) {
			status = "expiring"
		}
		rows[i] = []string{cert.contractorID, cert.expiry.Format(time.DateOnly), status}
	}
	return rows
}
