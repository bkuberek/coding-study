// Package store declares the entry type: cstudy grades Inventory, built with NewInventory.
package store

import "github.com/shopspring/decimal"

// Inventory counts stock by name.
type Inventory struct{}

// NewInventory returns an empty inventory.
func NewInventory() *Inventory {
	return &Inventory{}
}

// Add adds count to the stock of name and returns the new count.
func (i *Inventory) Add(name string, count int) int {
	panic("not implemented")
}

// Label is the stock of name as text.
func (i *Inventory) Label(name string) string {
	panic("not implemented")
}

// Value is the stock of name times price.
func (i *Inventory) Value(name string, price decimal.Decimal) decimal.Decimal {
	panic("not implemented")
}
