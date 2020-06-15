from univention.udm import UDM

from ucsschool.importer.utils.user_pyhook import UserPyHook
from univention.config_registry import ConfigRegistry
from univention.udm.exceptions import CreateError

ucr = ConfigRegistry()
ucr.load()
DEFAULT_HOSTNAME = ""
DEFAULT_OXDBSERVER = ""
DEFAULT_OXINTEGRATIONVERSION = ""

CONTEXT_IDS = []
DEFAULT_CONTEXT_ID = "10"


def set_default_values(contexts):
    global DEFAULT_OXINTEGRATIONVERSION, DEFAULT_HOSTNAME, DEFAULT_OXDBSERVER
    for context in contexts:
        if DEFAULT_CONTEXT_ID == context.props.contextid:
            DEFAULT_OXINTEGRATIONVERSION = context.props.oxintegrationversion
            DEFAULT_HOSTNAME = context.props.hostname
            DEFAULT_OXDBSERVER = context.props.oxDBServer


class CreateNewContexts(UserPyHook):
    supports_dry_run = False

    priority = {
        "pre_create": 1,
        "post_create": None,
        "pre_modify": 1,
        "post_modify": None,
        "pre_move": None,
        "post_move": None,
        "pre_remove": None,
        "post_remove": None,
    }

    def _check_context(self, user):
        udm = UDM(self.lo).version(1)
        mod = udm.get("oxmail/oxcontext")
        if not CONTEXT_IDS:
            global CONTEXT_IDS
            contexts = mod.search()
            set_default_values(contexts)
            CONTEXT_IDS = [context["oxContextIDNum"][0] for _, context in contexts]

        if not self.dry_run:
            ci = user.udm_properties.get("oxContext", "")
            if ci and ci not in CONTEXT_IDS:
                try:
                    ox_context = mod.new()
                    ox_context.position = "cn=open-xchange,{}".format(
                        ucr.get("ldap/base")
                    )
                    ox_context.props.name = "context{}".format(ci)
                    ox_context.props.contextid = ci
                    ox_context.props.hostname = DEFAULT_HOSTNAME
                    ox_context.props.oxintegrationversion = DEFAULT_OXINTEGRATIONVERSION
                    ox_context.props.oxDBServer = DEFAULT_OXDBSERVER
                    ox_context.save()
                    self.logger.info("Created UDM object for OX-context {}.".format(ci))
                except CreateError:
                    global CONTEXT_IDS
                    self.logger.info("OX-context {} already exists.".format(ci))
                    CONTEXT_IDS.append(ci)

    def pre_create(self, user):
        self.logger.info("Running a post_create hook for %s.", user)
        self._check_context(user)

    def pre_modify(self, user):
        self.logger.debug("Running a post_modify hook for %s.", user)
        self._check_context(user)
