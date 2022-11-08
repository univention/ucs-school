from generic_user import GenericUser, PagesGenericUser
from tasks.bff_groups.groups_post import create_group
from tasks.bff_groups.groups_search_get import search_groups
from tasks.bff_groups.pages_listView_settings_get import get_pages_listView_settings
from tasks.bff_groups.token_post import token_post


class CreateGroupWorkgroup(GenericUser):
    group_type = "workgroup"
    tasks = [create_group]


class CreateGroupClass(GenericUser):
    group_type = "school_class"
    tasks = [create_group]


class SearchGroupClass(GenericUser):
    search_type = "school_class"
    tasks = [search_groups]


class SearchGroupWorkgroup(GenericUser):
    search_type = "workgroup"
    tasks = [search_groups]


class GetPagesListViewSettings(PagesGenericUser):
    tasks = [get_pages_listView_settings]


class GetToken(GenericUser):
    tasks = [token_post]

    def on_start(self):
        pass
