import time


class RateLimitExceeded(Exception):
    pass


class RateLimiter:
    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self.clients = {}

    def check(self, client_id: str):
        if self.per_minute <= 0:
            return

        now = time.time()
        window = int(now / 60)

        if client_id not in self.clients or self.clients[client_id]["window"] != window:
            self.clients[client_id] = {"window": window, "count": 0}

        self.clients[client_id]["count"] += 1

        if self.clients[client_id]["count"] > self.per_minute:
            raise RateLimitExceeded()
