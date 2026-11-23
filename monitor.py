import time

import requests


def check_url(url, timeout=10):
    """Check if a URL is reachable and return its status.

    Args:
        url: The URL to check.
        timeout: Request timeout in seconds.

    Returns:
        A dict with keys: url, status_code, response_time_ms, is_up.
        If the request fails, status_code is 0 and is_up is False.
    """
    try:
        start = time.time()
        response = requests.get(url, timeout=timeout)
        elapsed_ms = round((time.time() - start) * 1000, 2)

        return {
            "url": url,
            "status_code": response.status_code,
            "response_time_ms": elapsed_ms,
            "is_up": response.status_code < 400,
        }
    except requests.RequestException as e:
        elapsed_ms = round((time.time() - start) * 1000, 2)
        return {
            "url": url,
            "status_code": 0,
            "response_time_ms": elapsed_ms,
            "is_up": False,
            "error": str(e),
        }
