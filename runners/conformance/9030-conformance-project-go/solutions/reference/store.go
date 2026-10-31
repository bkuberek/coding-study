// Package store declares the entry type: cstudy grades Inventory, built with NewInventory.
//
// The package spreads over two files (inventory_counts.go holds the counts) and imports a package
// of its module by import path and the vendored decimal module, which a grading build reaches
// through the project's go.work.
package store

import (
	"conformance-project-go/labels"

	"github.com/shopspring/decimal"
)

// Inventory counts stock by name.
type Inventory struct {
	counts counts
}

// NewInventory returns an empty inventory.
func NewInventory() *Inventory {
	return &Inventory{counts: counts{}}
}

// Add adds count to the stock of name and returns the new count.
func (i *Inventory) Add(name string, count int) int {
	return i.counts.add(name, count)
}

// Label is the stock of name as text.
func (i *Inventory) Label(name string) string {
	return labels.For(name, i.counts[name])
}

// Value is the stock of name times price.
func (i *Inventory) Value(name string, price decimal.Decimal) decimal.Decimal {
	return decimal.NewFromInt(int64(i.counts[name])).Mul(price)
}
