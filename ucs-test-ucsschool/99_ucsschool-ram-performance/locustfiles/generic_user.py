import os

from faker import Faker
from locust import constant_pacing, events
from locustclasses import UiUserClient
from utils import TestCleaner, TestData, get_settings

ROLES = ["student", "teacher"]

test_cleaner: TestCleaner = TestCleaner()


@events.quit.add_listener
def clean_test_env(*args, **kwargs):
    test_cleaner.delete()


class GenericUser(UiUserClient):
    abstract = True
    wait_time = constant_pacing(float(os.getenv("LOCUST_WAIT_TIME", 1)))

    def __init__(self, *args, **kwargs):
        self.settings = get_settings()
        self.fake = Faker()
        self.test_data: TestData = TestData()
        self.test_cleaner = test_cleaner

        super(GenericUser, self).__init__(*args, **kwargs)
        self.username = self.settings.BFF_TEST_ADMIN_USERNAME  # nosec
        self.password = self.settings.BFF_TEST_ADMIN_PASSWORD  # nosec


class PagesGenericUser(GenericUser):
    abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = self.test_data.random_school()
        self.username = self.test_data.random_user(self.school)
