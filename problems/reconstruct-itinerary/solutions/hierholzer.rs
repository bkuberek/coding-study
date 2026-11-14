use std::collections::HashMap;

const START: &str = "JFK";

pub fn find_itinerary(tickets: Vec<Vec<String>>) -> Vec<String> {
    // Destinations sorted in decreasing order, so pop() always takes the smallest unused one.
    let mut destinations: HashMap<&str, Vec<&str>> = HashMap::new();
    for ticket in &tickets {
        destinations
            .entry(ticket[0].as_str())
            .or_default()
            .push(ticket[1].as_str());
    }
    for targets in destinations.values_mut() {
        targets.sort_unstable_by(|a, b| b.cmp(a));
    }
    let mut route = Vec::with_capacity(tickets.len() + 1);
    let mut stack = vec![START];
    while let Some(&airport) = stack.last() {
        match destinations.get_mut(airport).and_then(Vec::pop) {
            Some(next) => stack.push(next),
            None => {
                // Stuck: this airport comes last among what is left, so it joins the route now.
                route.push(airport);
                stack.pop();
            }
        }
    }
    route.reverse();
    route.into_iter().map(String::from).collect()
}
