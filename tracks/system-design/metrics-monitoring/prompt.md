# Metrics and Monitoring

## Question

Design the internal metrics platform for a large engineering organization: every service and host emits metrics, engineers build dashboards on them, and alert rules page the on-call engineer when something is wrong. Logs and traces are out of scope.

## Functional requirements

- Ingest counters, gauges and histograms, each identified by a metric name and a set of labels (`service`, `region`, `status_code`, and so on), sent by an agent on every host.
- Query with filters on labels, aggregation and grouping across series, rates and percentiles over arbitrary time ranges, for dashboards and ad hoc investigation.
- Alert rules are queries with thresholds and durations ("error ratio above 2% for 5 minutes"); notifications go to a pager or chat, grouped and deduplicated, with silences during maintenance.
- Retention: raw 10-second samples for 15 days, 1-minute rollups for 90 days, 1-hour rollups for 2 years.
- Many teams share the platform; each team sees usage and limits for its own metrics.

## Non-functional requirements

- New samples are queryable within 30 seconds; an alert fires within 1 minute of the condition becoming true.
- Dashboards over the last hour load in under 1 second at p99; queries over months may take a few seconds.
- No data loss in normal operation; under overload, degrade predictably instead of failing everywhere.
- The platform must keep alerting during the incidents it exists to detect, including a regional outage.
- One team's mistake, such as putting a user id in a label, must not degrade the platform for everyone else.

## Scale

- 200 million active time series, each reporting every 10 seconds.
- 20 million new series per day from short-lived containers and deploys.
- 50,000 alert rules evaluated every 30 seconds.
- 2,000 engineers viewing dashboards at peak, each dashboard refreshing 20 panels every 30 seconds.
