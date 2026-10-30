package debug_shadowed_variable

import (
	"fmt"
	"strconv"
	"strings"
)

func checkoutTotal(prices []int, coupon string) int {
	subtotal := 0
	for _, price := range prices {
		subtotal += price
	}
	discount := 0
	if coupon != "" {
		// `discount, err := ...` here would declare a second discount that lives only in this
		// block; plain assignment sets the one declared above.
		var err error
		discount, err = couponDiscount(coupon, subtotal)
		if err != nil {
			return -1
		}
		if discount > subtotal {
			discount = subtotal
		}
	}
	return subtotal - discount
}

// couponDiscount returns the discount, in cents, that coupon grants on subtotal.
func couponDiscount(coupon string, subtotal int) (int, error) {
	switch {
	case strings.HasPrefix(coupon, "PCT"):
		percent, err := strconv.Atoi(coupon[len("PCT"):])
		if err != nil || percent < 1 || percent > 100 {
			return 0, fmt.Errorf("bad percentage in coupon %q", coupon)
		}
		return subtotal * percent / 100, nil
	case strings.HasPrefix(coupon, "OFF"):
		cents, err := strconv.Atoi(coupon[len("OFF"):])
		if err != nil || cents < 1 {
			return 0, fmt.Errorf("bad amount in coupon %q", coupon)
		}
		return cents, nil
	}
	return 0, fmt.Errorf("unknown coupon %q", coupon)
}
