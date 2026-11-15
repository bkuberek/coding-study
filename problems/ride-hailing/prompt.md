# Ride Hailing

## Question

Design the core of a ride-hailing service: riders request a ride, the system finds a nearby driver, and both follow the trip in real time until it ends. Payments, driver onboarding and maps (routing and ETAs) exist as services you can call.

## Functional requirements

- Online drivers send their location every 4 seconds.
- A rider enters pickup and destination and sees a price and an estimated pickup time before confirming. The price includes surge pricing when demand outstrips supply.
- On confirmation the system offers the trip to a suitable nearby driver, who has 10 seconds to accept; if they decline or time out, the next driver gets the offer.
- Trips move through requested, driver assigned, driver arrived, in progress, completed, or cancelled by either side; both apps show the other party's live location.
- When the trip completes, the payment service is asked to charge the rider.

## Non-functional requirements

- A driver is never assigned to two trips at once, and a confirmed request is never silently dropped.
- From confirmation to the first offer reaching a driver: under 1 second at p99.
- Location updates reach the other party's app within 2 seconds.
- Trip state is 99.99% available, and trips in progress can complete even during a regional incident.
- The price a rider confirmed is the price they pay (for the same route).

## Scale

- 2 million drivers online at the global peak.
- 20 million trips per day; 1,000 ride requests per second at the global peak, and 10 price quotes for every request.
- The largest city has 100,000 drivers online and 50 requests per second at its peak.
- Demand spikes locally and suddenly: a concert ending, rain starting, a stadium emptying.
