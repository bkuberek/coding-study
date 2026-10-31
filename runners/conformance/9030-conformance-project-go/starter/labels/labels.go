// Package labels formats stock counts; the entry's package imports it by its import path.
package labels

import "strconv"

// Separator goes between a name and its count.
const Separator = ": "

// For is the label of a name and its count.
func For(name string, count int) string {
	return name + Separator + strconv.Itoa(count)
}
