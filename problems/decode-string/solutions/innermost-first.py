def decode_string(s: str) -> str:
    while "[" in s:
        # The first "]" closes an innermost group: the last "[" before it is its opener.
        close = s.index("]")
        open_ = s.rindex("[", 0, close)
        start = open_
        while start > 0 and s[start - 1].isdigit():
            start -= 1
        count = int(s[start:open_])
        s = s[:start] + s[open_ + 1 : close] * count + s[close + 1 :]
    return s
