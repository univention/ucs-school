import logging
import time
from typing import Optional, Set

import requests
from gevent.lock import BoundedSemaphore
from locust import HttpUser
from utils import AuthToken, get_settings, retrieve_token

settings = get_settings()


class UiUserClient(HttpUser):
    abstract = True
    auth_token: AuthToken = None  # share token with all threads

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    def on_start(self):
        logging.info("Starting client with user %r (ID: %r).", self.username, id(self))
        self.get_token(self.username, self.password)  # prefetch token

    @classmethod
    def get_token(cls, username: str, password: str) -> str:
        with BoundedSemaphore():  # prevent multiple threads fetching a token at the same time
            if not cls.auth_token or cls.auth_token.expired:
                cls.auth_token = retrieve_token(username, password)
                logging.info("Renewed token for %r.", username)
                logging.info(
                    "Token expires in %.1f seconds.", cls.auth_token.expiration_time - time.time()
                )
                logging.info("Token: %r...%r", cls.auth_token.token[:30], cls.auth_token.token[-30:])
            return cls.auth_token.token

    def request(
        self,
        operation: str,
        *args,
        add_auth_token: bool = True,
        headers: Optional[dict] = None,
        response_codes: Optional[Set] = None,
        **kwargs
    ) -> requests.Response:
        """Wrapper method for HttpUser.client.post, adds auth token automatically"""

        headers = headers or {}

        if "accept" not in headers:
            headers["accept"] = "application/json"

        if "Accept-Language" not in headers:
            headers["Accept-Language"] = "en-US"

        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        if add_auth_token:
            headers["Authorization"] = f"Bearer {self.get_token(self.username, self.password)}"
        assert operation in {"get", "post", "put", "delete", "patch"}
        r = getattr(self.client, operation)(*args, headers=headers, **kwargs)
        if response_codes and r.status_code not in response_codes:
            logging.error("Request failed for url %r with status code %r.", r.url, r.status_code)
            logging.error(
                "operation=%r *args=%r add_auth_token=%r headers=%r response_codes=%r kwargs=%r",
                operation,
                args,
                add_auth_token,
                headers,
                response_codes,
                kwargs,
            )
            logging.error("Response content: %r", r.content)
        return r
