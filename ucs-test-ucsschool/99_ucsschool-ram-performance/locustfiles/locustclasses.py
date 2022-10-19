from typing import Optional

import requests
from locust import HttpUser
from utils import get_token


class UiUserClient(HttpUser):
    abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self._auth_token: Optional[str] = None

    def on_start(self):
        print(f"{self.username}, {id(self)}")
        self._auth_token = get_token(username=self.username, password=self.password)

    def post(
        self, *args, add_auth_token: bool = True, headers: Optional[dict] = None, **kwargs
    ) -> requests.Response:
        """Wrapper method for HttpUser.client.post, adds auth token automatically"""

        if not headers:
            headers = {"accept": "application/json", "Accept-Language": "en-US"}

        if "accept" not in headers:
            headers.update({"accept": "application/json"})

        if "Accept-Language" not in headers:
            headers.update({"Accept-Language": "en-US"})

        if add_auth_token:
            headers.update({"Authorization": f"Bearer {self._auth_token}"})

        return self.client.post(*args, headers=headers, **kwargs)
