import logging
import multiprocessing
import os
import subprocess
import sys
import time
from typing import Optional, Set

import requests
from gevent.lock import BoundedSemaphore
from locust import HttpUser, events
from utils import AuthToken, get_settings, retrieve_token

settings = get_settings()


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    if environment.parsed_options.master:
        environment.worker_processes = []
        master_args = [*sys.argv]
        worker_args = [sys.argv[0]]
        if "-f" in master_args:
            i = master_args.index("-f")
            worker_args += [master_args.pop(i), master_args.pop(i)]
        if "--locustfile" in master_args:
            i = master_args.index("--locustfile")
            worker_args += [master_args.pop(i), master_args.pop(i)]
        worker_args += ["--worker"]
        workers = multiprocessing.cpu_count() - 1
        workers = workers if workers > 0 else 1
        for _ in range(workers):
            p = subprocess.Popen(
                worker_args,
                start_new_session=True,
                # LOCUST_RUN_TIME not allowed for workers
                env={k: v for k, v in os.environ.items() if k != "LOCUST_RUN_TIME"},
            )
            environment.worker_processes.append(p)


class UiUserClient(HttpUser):
    abstract = True
    auth_token: AuthToken = None  # share token with all threads
    token_sem = BoundedSemaphore()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    def on_start(self):
        logging.info("Starting client with user %r (ID: %r).", self.username, id(self))
        self.get_token(self.username, self.password)  # prefetch token

    @classmethod
    def get_token(cls, username: str, password: str) -> str:
        cls.token_sem.acquire()  # prevent multiple threads fetching a token at the same time
        if not cls.auth_token or cls.auth_token.expired:
            cls.auth_token = retrieve_token(username, password)
            logging.info("Renewed token for %r.", username)
            logging.info("Token expires in %.1f seconds.", cls.auth_token.expiration_time - time.time())
            logging.info("Token: %r...%r", cls.auth_token.token[:30], cls.auth_token.token[-30:])
        cls.token_sem.release()
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
        header_keys = {h.lower() for h in headers}

        if "accept" not in header_keys:
            headers["accept"] = "application/json"

        if "accept-language" not in header_keys:
            headers["accept-language"] = "en-US"

        if "content-type" not in header_keys:
            headers["content-type"] = "application/json"

        if add_auth_token:
            headers["authorization"] = f"Bearer {self.get_token(self.username, self.password)}"
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
            if r.status_code == 401:
                with BoundedSemaphore():
                    self.auth_token = None
        return r
