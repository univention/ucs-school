from generic_user import GenericUser, PagesGenericUser
from tasks.bff_users.groups_get import get_groups
from tasks.bff_users.pages_addView_settings_get import get_pages_addView_settings
from tasks.bff_users.pages_listView_settings_get import get_pages_listView_settings
from tasks.bff_users.token_post import token_post
from tasks.bff_users.user_delete import delete_user
from tasks.bff_users.user_get import get_user
from tasks.bff_users.user_patch import modify_user
from tasks.bff_users.user_post import create_user
from tasks.bff_users.user_search_get import search_user


class CreateUser(GenericUser):
    tasks = [create_user]


class DeleteUser(GenericUser):
    tasks = [delete_user]


class ModifyUserScenario1(GenericUser):
    scenario = 1
    tasks = [modify_user]


class ModifyUserScenario2(GenericUser):
    scenario = 2
    tasks = [modify_user]


class ModifyUserScenario3(GenericUser):
    scenario = 3
    tasks = [modify_user]


class UserSearchGet(GenericUser):
    tasks = [search_user]
    search_type = 1


class GetUser(GenericUser):
    tasks = [get_user]


class GetGroups(GenericUser):
    tasks = [get_groups]


class GetPagesAddViewSettings(PagesGenericUser):
    tasks = [get_pages_addView_settings]


class GetPagesListViewSettings(PagesGenericUser):
    tasks = [get_pages_listView_settings]


class GetToken(GenericUser):
    tasks = [token_post]

    def on_start(self):
        pass


class RealUser(GenericUser):
    tasks = {create_user: 1, delete_user: 1, modify_user: 1, search_user: 1, get_user: 5, get_groups: 1}
    search_type = 1
