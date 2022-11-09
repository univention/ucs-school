import logging
import time
from typing import Dict, Optional, Set

import requests
from locust import HttpUser
from utils import get_settings, get_token_info

settings = get_settings()


class UiUserClient(HttpUser):
    abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self._auth_token: Optional[str] = None
        self._auth_token_info: Optional[Dict] = None
        self._expiration_time: int = 0

    def on_start(self):
        logging.info(f"Starting client with user {self.username}, {id(self)}")
        self.check_auth()

    def check_auth(self):
        if (
            self._auth_token is None
            or self._expiration_time - time.time() <= settings.BFF_TEST_TOKEN_RENEW_PERIOD
        ):
            self._auth_token_info = get_token_info(username=self.username, password=self.password)
            self._auth_token = self._auth_token_info["access_token"]
            self._expiration_time = time.time() + self._auth_token_info["expires_in"]
            print(f"Renewed token for {self.username}")
            print(f"Token expires in {self._expiration_time - time.time()} seconds")
            print(f"Token {self._auth_token}")

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

        self.check_auth()

        if not headers:
            headers = {"accept": "application/json", "Accept-Language": "en-US"}

        if "accept" not in headers:
            headers.update({"accept": "application/json"})

        if "Accept-Language" not in headers:
            headers.update({"Accept-Language": "en-US"})

        if add_auth_token:
            headers.update({"Authorization": f"Bearer {self._auth_token}"})
        assert operation in ["get", "post", "put", "delete", "patch"]
        r = getattr(self.client, operation)(*args, headers=headers, **kwargs)
        if response_codes and r.status_code not in response_codes:
            logging.error(f"Request failed for url {r.url} with status code {r.status_code}")
            logging.error(f"Response content: {r.content}")
        return r
