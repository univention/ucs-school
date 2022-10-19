import random

from faker import Faker
from locust import constant_pacing, events, task
from locustclasses import UiUserClient
from utils import TestCleaner, TestData, get_settings

ROLES = ["student", "teacher"]

settings = get_settings()

fake = Faker()

test_data: TestData = TestData()
test_cleaner: TestCleaner = TestCleaner()


@events.quit.add_listener
def clean_test_env(*args, **kwargs):
    test_cleaner.delete()


class CreateUserClient(UiUserClient):

    wait_time = constant_pacing(1)

    def __init__(self, *args, **kwargs):
        super(CreateUserClient, self).__init__(*args, **kwargs)
        self.username = settings.BFF_TEST_ADMIN_USERNAME  # nosec
        self.password = settings.BFF_TEST_ADMIN_PASSWORD  # nosec

    @task
    def create_user(self):
        name = fake.unique.pystr(max_chars=15)

        school = test_data.random_school()
        school_class = test_data.random_class(school)

        json = {
            "name": name,
            "firstname": fake.first_name(),
            "lastname": fake.last_name(),
            "school": school,
            "schoolClasses": [school_class],
            "role": random.choice(ROLES),  # nosec
        }
        url = f"https://{settings.BFF_USERS_HOST}/ucsschool/bff-users/v1/users/"
        r = self.post(url, json=json)
        test_cleaner.delete_later_user(name)
        assert r.status_code == 201
