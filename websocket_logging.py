"""Keep handshake diagnostics for requests that were actually sent."""

import logging
from websockets.exceptions import InvalidMessage


class IgnoreEmptyHandshakes(logging.Filter):
    def filter(self, record):
        if record.getMessage() != "opening handshake failed" or not record.exc_info:
            return True
        error = record.exc_info[1]
        if not isinstance(error, InvalidMessage):
            return True
        request_error = error.__cause__
        stream_error = getattr(request_error, "__cause__", None)
        # A canceled browser connection or TCP probe isn't a malformed request.
        # Keep errors for partial request lines, missing headers, and bad HTTP.
        empty_request = (
            isinstance(request_error, EOFError)
            and str(request_error) == "connection closed while reading HTTP request line"
            and isinstance(stream_error, EOFError)
            and str(stream_error) == "stream ends after 0 bytes, before end of line"
        )
        return not empty_request
