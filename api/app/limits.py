from time import monotonic
from typing import Dict


class TokenBucket:
    def __init__(self, rate_per_min: int, burst: int):
        self.rate = rate_per_min / 60.0
        self.capacity = burst
        self.tokens = float(burst)
        self.updated = monotonic()

    def allow(self) -> bool:
        now = monotonic()
        elapsed = now - self.updated
        self.updated = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimiter:
    def __init__(self, rate_per_min: int = 6, burst: int = 6):
        self.rate = rate_per_min
        self.burst = burst
        self.buckets: Dict[str, TokenBucket] = {}

    def bucket(self, key: str) -> TokenBucket:
        b = self.buckets.get(key)
        if not b:
            b = TokenBucket(self.rate, self.burst)
            self.buckets[key] = b
        return b

    def allow(self, key: str) -> bool:
        return self.bucket(key).allow()


limiter = RateLimiter(rate_per_min=6, burst=6)
