import smtplib

import cStringIO

from ucsschool.importer.utils.result_pyhook import ResultPyHook
from univention.config_registry import ConfigRegistry

# Set this to True, if emails should also be sent when a dry-run is executed:
SEND_AFTER_DRY_RUN = False

ucr = ConfigRegistry()
ucr.load()

from_address = "ucs-school-import@{}.{}".format(ucr["hostname"], ucr["domainname"])
to_addresses = ["root@{}.{}".format(ucr["hostname"], ucr["domainname"])]
smtp_server = "localhost"


class MailResultHook(ResultPyHook):
    priority = {
        "user_result": 1,
    }
    supports_dry_run = True

    def user_result(self, user_import_data):
        if self.dry_run and not SEND_AFTER_DRY_RUN:
            self.logger.info("Not sending result email in dry-run.")
            return

        msg = cStringIO.StringIO()
        msg.write("From: {}\n".format(from_address))
        msg.write("To: {}\r\n\r\n".format(", ".join(to_addresses)))

        msg.write("There have been {} errors.\n".format(len(user_import_data.errors)))
        for error in user_import_data.errors:
            msg.write("    {!s}".format(error))

        added = sum(len(users) for users in user_import_data.added_users.values())
        msg.write("Users created ({}):\n".format(added))
        for role, users in user_import_data.added_users.items():
            if not users:
                continue
            msg.write("    {}: {}\n".format(role, ", ".join([u["name"] for u in users[:4]])))
            for user_chunk in [users[i : i + 4] for i in range(4, len(users), 4)]:
                msg.write(
                    "      {}{}\n".format(" " * len(role), ", ".join([u["name"] for u in user_chunk]))
                )

        modified = sum(len(users) for users in user_import_data.modified_users.values())
        msg.write("Users modified ({}):\n".format(modified))
        for role, users in user_import_data.modified_users.items():
            if not users:
                continue
            msg.write("    {}: {}\n".format(role, ", ".join([u["name"] for u in users[:4]])))
            for user_chunk in [users[i : i + 4] for i in range(4, len(users), 4)]:
                msg.write(
                    "      {}{}\n".format(" " * len(role), ", ".join([u["name"] for u in user_chunk]))
                )

        deleted = sum(len(users) for users in user_import_data.deleted_users.values())
        msg.write("Users deleted ({}):\n".format(deleted))
        for role, users in user_import_data.deleted_users.items():
            if not users:
                continue
            msg.write("    {}: {}\n".format(role, ", ".join([u["name"] for u in users[:4]])))
            for user_chunk in [users[i : i + 4] for i in range(4, len(users), 4)]:
                msg.write(
                    "      {}{}\n".format(" " * len(role), ", ".join([u["name"] for u in user_chunk]))
                )

        server = smtplib.SMTP(smtp_server)
        server.set_debuglevel(1)
        server.sendmail(from_address, to_addresses, msg.getvalue())
        msg.close()
        server.quit()
