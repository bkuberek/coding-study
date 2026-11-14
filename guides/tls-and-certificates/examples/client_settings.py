"""What Python's TLS client checks by default, and the two switches that turn the checks off."""

import ssl

context = ssl.create_default_context()
print("verify_mode:   ", context.verify_mode.name)
print("check_hostname:", context.check_hostname)
print("TLS 1.2 or newer only:", context.minimum_version >= ssl.TLSVersion.TLSv1_2)
print("falls back to the common name:", context.hostname_checks_common_name)

try:
    context.verify_mode = ssl.CERT_NONE
except ValueError as error:
    print("ValueError:", error)

# Turning verification off takes two steps, in this order. Both are mistakes in a client.
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
print("after both:", context.verify_mode.name, context.check_hostname)

server_side = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
print("a server context checks clients:", server_side.verify_mode.name)
