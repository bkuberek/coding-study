package reconstruct_itinerary

import "slices"

const start = "JFK"

func findItinerary(tickets [][]string) []string {
	// Destinations sorted in decreasing order, so taking the last one always takes the smallest.
	destinations := make(map[string][]string)
	for _, ticket := range tickets {
		destinations[ticket[0]] = append(destinations[ticket[0]], ticket[1])
	}
	for _, targets := range destinations {
		slices.Sort(targets)
		slices.Reverse(targets)
	}
	route := make([]string, 0, len(tickets)+1)
	stack := []string{start}
	for len(stack) > 0 {
		airport := stack[len(stack)-1]
		if targets := destinations[airport]; len(targets) > 0 {
			destinations[airport] = targets[:len(targets)-1]
			stack = append(stack, targets[len(targets)-1])
		} else {
			// Stuck: this airport comes last among what is left, so it joins the route now.
			route = append(route, airport)
			stack = stack[:len(stack)-1]
		}
	}
	slices.Reverse(route)
	return route
}
