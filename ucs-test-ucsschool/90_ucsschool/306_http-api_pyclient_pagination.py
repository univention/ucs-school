#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v -s
## -*- coding: utf-8 -*-
## desc: Import HTTP API Python client stops iterating when a follow-up page is empty
## tags: [apptest,ucsschool,ucsschool_import1,ucs-school-import]
## exposure: safe
## packages:
##   - ucs-school-import-http-api-client
## bugs: [60101]

from typing import Any

import pytest

from ucsschool.http_api.client import ResourceRepresentation, ResourceRepresentationIterator

Page = dict[str, Any]

NEXT_URL = "https://primary.example.com/api/v1/imports/users/?limit=2&offset=2"
FIRST_PAGE: Page = {"count": 3, "next": NEXT_URL, "previous": None, "results": [{"id": 1}, {"id": 2}]}


class StubResourceClient:
    pages: list[Page]

    def __init__(self, pages: list[Page]) -> None:
        self.pages = pages

    def _resource_from_url(self, url: str, **params: Any) -> Page:
        return self.pages.pop(0)


@pytest.fixture(autouse=True)
def identity_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    def get_repr(resource_client: StubResourceClient, resource: Page) -> Page:
        return resource

    monkeypatch.setattr(ResourceRepresentation, "get_repr", get_repr)


def test_iterates_across_pages() -> None:
    client = StubResourceClient([{"count": 3, "next": None, "previous": None, "results": [{"id": 3}]}])
    jobs = ResourceRepresentationIterator(client, dict(FIRST_PAGE))

    assert next(jobs) == {"id": 1}
    assert next(jobs) == {"id": 2}
    assert next(jobs) == {"id": 3}
    with pytest.raises(StopIteration):
        next(jobs)


def test_empty_follow_up_page_raises_stop_iteration() -> None:
    client = StubResourceClient([{"count": 2, "next": None, "previous": None, "results": []}])
    jobs = ResourceRepresentationIterator(client, dict(FIRST_PAGE))

    assert next(jobs) == {"id": 1}
    assert next(jobs) == {"id": 2}
    with pytest.raises(StopIteration):
        next(jobs)


def test_empty_follow_up_page_with_next_is_skipped() -> None:
    client = StubResourceClient(
        [
            {"count": 3, "next": NEXT_URL, "previous": None, "results": []},
            {"count": 3, "next": None, "previous": None, "results": [{"id": 3}]},
        ]
    )
    jobs = ResourceRepresentationIterator(client, dict(FIRST_PAGE))

    assert list(jobs) == [{"id": 1}, {"id": 2}, {"id": 3}]
