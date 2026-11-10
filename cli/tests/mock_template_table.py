"""What a run-time value in a mock response may say, one table for its two readers: the mock server,
which fills a value in and sends anything else as written, and S20, which refuses a `{{` that opens
no value before any stack starts. The mock server runs alone, on the standard library, so it cannot
share S20's code; this table keeps the two the same."""

VALUES = [
    "{{request.method}}",
    "{{request.path}}",
    "{{request.body}}",
    "{{request.body.model}}",
    "{{request.body.messages.0.content}}",
    "{{request.body.max_tokens}}",
    "{{request.query.date}}",
    "{{request.headers.x-request-id}}",
    "{{seq}}",
    "{{len(request.body.messages)}}",
    "{{words(request.body.messages)}}",
    "{{json(request.body.model)}}",
]
NOT_VALUES = [
    "{{model}}",
    "{{ request.body.model }}",
    "{{request.body.}}",
    "{{request.cookies.a}}",
    "{{request.query}}",
    "{{len(seq}}",
    "{{upper(request.body.model)}}",
    "{{len(len(request.body))}}",
    "{{now_s}}",
    "{{",
]
