# SMS messages are limited to 160 characters per segment (GSM-7).
MAX_SEGMENT_CHARS = 160


def min_sms_segments(message):
    """Minimum number of SMS segments needed to deliver `message`.

    Words are packed into the fewest segments possible while respecting
    the 160-character limit. If a single word is longer than 160 chars,
    it is split into chunks so the function still returns a sensible
    segment count.
    """
    if not isinstance(message, str) or not message.strip():
        return 0

    words = message.split()
    if not words:
        return 0

    tokens = []
    for word in words:
        if len(word) > MAX_SEGMENT_CHARS:
            for start in range(0, len(word), MAX_SEGMENT_CHARS):
                tokens.append(word[start:start + MAX_SEGMENT_CHARS])
        else:
            tokens.append(word)

    segments = 0
    current_len = 0
    for token in tokens:
        token_len = len(token)
        add = token_len if current_len == 0 else token_len + 1
        if current_len + add > MAX_SEGMENT_CHARS:
            segments += 1
            current_len = token_len
        else:
            current_len += add

    return segments + 1 if segments < len(tokens) else 1 if tokens else 0
