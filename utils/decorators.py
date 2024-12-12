import werkzeug
from odoo import http
from logging import getLogger
import functools
import time
import random
import string


_logger = getLogger(__name__)

KEY_IDENTIFIER = "API_KEY"
# API_KEY = "ORCLTESTME@123"
API_KEY = "796df22fcd7e153461c1e2128b8a203e46191037fbf094f69ff60c1d3116c27e"

__all__ = ["logTracer", "authKeyRequired"]


def random_str(length=7):
    characters = string.ascii_uppercase + string.digits
    random_string = "".join(random.choice(characters) for _ in range(length))
    return random_string


def logTracer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Start time
        start_time = time.time()
        _sequence = random_str()

        # Log request details
        request = http.request.httprequest
        _logger.info(f"------------------------ START REQUEST < {_sequence} > ------------------------")
        _logger.info(f"CLASS_METHOD: {func.__qualname__!r}")
        _logger.info(f"REQUEST_METHOD: {request.method!r}")
        _logger.info(f"REQUEST_URL: {request.url!r}")
        _logger.info(f"REQUEST_HEADERS: {dict(request.headers)}")
        _logger.info(f"REQUEST_PARAMS: {request.args!r}")
        _logger.info(f"REQUEST_BODY: {kwargs!r}")

        # Execute the function and get the response
        response = func(*args, **kwargs)

        # End time
        end_time = time.time()

        # Calculate the response time
        response_time = end_time - start_time

        # Log response details and response time
        _logger.info(f"RESPONSE_BODY: {response}")
        _logger.info(f"RESPONSE_TTL: {response_time:.4f} seconds")
        _logger.info(f"------------------------ END REQUEST < {_sequence} > ------------------------")
        return response

    return wrapper


def authKeyRequired(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        api_key = kwargs.get(KEY_IDENTIFIER)
        if not bool(api_key) or api_key != API_KEY:
            _logger.error("User has provided wrong key to access the API.")
            # werkzeug.exceptions.abort(http.Response({"error": "Invalid API Key"}, status=401))
            raise werkzeug.exceptions.Unauthorized({"error": "Invalid API Key !!!"})
        response = func(*args, **kwargs)

        return response

    return wrapper
