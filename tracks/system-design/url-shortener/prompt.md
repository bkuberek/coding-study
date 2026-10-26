# URL Shortener

## Question

Design the link shortening service behind a marketing platform. Customers paste a long URL and get a short link such as `https://sho.rt/Ab3dE9x`; anyone who opens the short link is redirected to the long URL, and the customer sees how often each link was opened.

## Functional requirements

- Create a short link for a long URL. The caller may request a custom alias (`sho.rt/spring-sale`) and an expiry time.
- Redirect a short link to its long URL. Expired or disabled links must stop redirecting.
- Owners can list their links and disable one, for example after it is reported as malicious.
- Click analytics per link: total clicks and clicks per day, broken down by country and referrer domain.

## Non-functional requirements

- Redirects are the product: p99 under 50 ms measured at the server, 99.99% availability.
- Link creation may be slower (p99 under 300 ms) and 99.9% available.
- A short link never redirects to the wrong destination, and generated codes are not sequential or easy to enumerate.
- Analytics may lag behind clicks by up to 5 minutes but must not lose more than 0.1% of clicks.
- A disabled malicious link stops redirecting within 1 minute everywhere.

## Scale

- 200 million new links per month, 5% of them with custom aliases.
- 100 redirects for every link created; traffic is heavily skewed: the top 1% of links receive half of all redirects.
- Peak traffic is 5 times the average.
- Links are kept for 5 years unless they expire earlier.
- Users are global; the service runs in three regions.
