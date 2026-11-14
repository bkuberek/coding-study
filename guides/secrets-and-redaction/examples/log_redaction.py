"""Masking credentials in log lines, and the place a redaction filter must sit to see every line."""

import logging
import re
import sys

CREDENTIAL = re.compile(r"(?i)(authorization: bearer |api_key=)[^\s&]+")


class Redact(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = CREDENTIAL.sub(r"\1[redacted]", record.getMessage())
        record.args = None
        return True


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(name)-8s %(message)s"))
app = logging.getLogger("app")
app.addHandler(handler)
app.setLevel(logging.INFO)
http = logging.getLogger("app.http")  # a child: its records go up to the handler of "app"

print("filter on the logger:")
redact = Redact()
app.addFilter(redact)
app.info("calling %s with authorization: Bearer %s", "/v1/orders", "f2c71d9a")
http.info("GET /v1/export?api_key=4e8a1b70&format=csv")

print("filter on the handler:")
app.removeFilter(redact)
handler.addFilter(redact)
app.info("calling %s with authorization: Bearer %s", "/v1/orders", "f2c71d9a")
http.info("GET /v1/export?api_key=4e8a1b70&format=csv")
