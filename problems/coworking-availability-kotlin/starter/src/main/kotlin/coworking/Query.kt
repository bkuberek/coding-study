package coworking

import java.net.URI
import java.net.URLDecoder

/** The first value of [name] in this target's query, decoded; empty when it has none. */
fun URI.queryValue(name: String): String =
    rawQuery.orEmpty()
        .split("&")
        .firstOrNull { it.startsWith("$name=") }
        ?.let { URLDecoder.decode(it.substringAfter("="), Charsets.UTF_8) }
        .orEmpty()
