from ucsschool.importer.utils.user_pyhook import SchoolPyHook
from ucsschool.lib.models.utils import ucr
from univention.config_registry import handler_set


class SelfServiceWhiteList(SchoolPyHook):
    supports_dry_run = True

    priority = {
        "post_create": 1,
    }
    ucr_variable_name = "umc/self-service/passwordreset/whitelist/groups"

    def post_create(self, school):
        allow_list = ucr.get(self.ucr_variable_name, [])
        ou = school.name
        allow_list.append("Domain Users {}".format(ou))
        res = "{}={}".format(self.ucr_variable_name, ",".join(allow_list))
        if self.dry_run:
            self.logger.info("Dry-run: skipping setting of {}.".format(res))
            return
        handler_set([res])
