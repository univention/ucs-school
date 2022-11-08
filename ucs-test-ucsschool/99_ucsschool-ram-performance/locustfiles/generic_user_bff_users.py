from generic_user import GenericUser, PagesGenericUser
from tasks.bff_users.user_post import create_user


class CreateUser(GenericUser):
    tasks = [create_user]
