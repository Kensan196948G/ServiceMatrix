"""slowapi レート制限設定"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

if os.getenv("TESTING", "false").lower() == "true":
    limiter = Limiter(key_func=get_remote_address, default_limits=[], enabled=False)
else:
    limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
