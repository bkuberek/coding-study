from collections.abc import Callable
from string import ascii_letters, digits

HTML_ENTITIES = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;"}
# Spelled out: str.isalnum() also accepts letters and digits of other scripts.
ASCII_ALPHANUMERIC = frozenset(ascii_letters + digits)
URL_UNRESERVED_BYTES = frozenset((ascii_letters + digits + "-._~").encode("ascii"))


def encode_html(text: str) -> str:
    return "".join(HTML_ENTITIES.get(character, character) for character in text)


def encode_url_query(text: str) -> str:
    return "".join(
        chr(byte) if byte in URL_UNRESERVED_BYTES else f"%{byte:02X}"
        for byte in text.encode("utf-8")
    )


def encode_js_string(text: str) -> str:
    # A Python str holds code points; JavaScript escapes name UTF-16 code units.
    encoded = text.encode("utf-16-be")
    escaped = []
    for start in range(0, len(encoded), 2):
        unit = int.from_bytes(encoded[start : start + 2], "big")
        character = chr(unit)
        escaped.append(character if character in ASCII_ALPHANUMERIC else f"\\u{unit:04X}")
    return "".join(escaped)


ENCODERS: dict[str, Callable[[str], str]] = {
    "html-text": encode_html,
    "html-attribute": encode_html,
    "url-query": encode_url_query,
    "js-string": encode_js_string,
}


def encode_output(text: str, context: str) -> str:
    encoder = ENCODERS.get(context)
    return encoder(text) if encoder is not None else ""
