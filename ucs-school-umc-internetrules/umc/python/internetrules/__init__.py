#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Defines and manages internet rules
#
# Copyright 2012-2023 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import fnmatch
import re

import six
from six.moves.urllib_parse import urlparse

import ucsschool.lib.internetrules as rules
import univention.admin.modules as udm_modules
import univention.admin.objects as udm_objects
import univention.config_registry
from ucsschool.lib.models.group import Group
from ucsschool.lib.school_umc_base import LDAP_Filter, SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.school_umc_ldap_connection import LDAP_Connection
from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import (
    BooleanSanitizer,
    ChoicesSanitizer,
    DictSanitizer,
    IntegerSanitizer,
    LDAPSearchSanitizer,
    ListSanitizer,
    StringSanitizer,
)

_ = Translation("ucs-school-umc-internetrules").translate

_filterTypes = {"whitelist": rules.WHITELIST, "blacklist": rules.BLACKLIST}
_filterTypesInv = {_i[1]: _i[0] for _i in _filterTypes.items()}


class Instance(SchoolBaseModule):
    @sanitize(
        pattern=LDAPSearchSanitizer(required=False, default="", use_asterisks=True, add_asterisks=True)
    )
    def query(self, request):
        """
        Searches for internet filter rules
        requests.options = {}
        'pattern' -- pattern to match within the rule name or the list of domains
        """
        MODULE.info("internetrules.query: options: %s" % (request.options,))
        pattern = request.options.get("pattern", "").lower()

        def _matchDomain(domains):
            # helper function to match pattern within the list of domains
            matches = [idom for idom in domains if pattern in idom.lower()]
            return 0 < len(matches)

        # filter out all rules that match the given pattern
        result = [
            {
                "name": irule.name,
                "type": _filterTypesInv[irule.type],
                "domains": len(irule.domains),
                "priority": irule.priority,
                "wlan": irule.wlan,
            }
            for irule in rules.list()
            if pattern in irule.name.lower()
            or _matchDomain(irule.domains)
            or fnmatch.fnmatchcase(irule.name, pattern)
        ]
        MODULE.info("internetrules.query: results: %s" % (result,))
        self.finished(request.id, result)

    @sanitize(StringSanitizer())
    def get(self, request):
        """
        Returns the specified rules
        requests.options = [ <ruleName>, ... ]
        """
        MODULE.info("internetrules.get: options: %s" % (request.options,))
        result = []
        # fetch all rules with the given names (we need to make sure that "name" is UTF8)
        names = set(request.options)
        result = [
            {
                "name": irule.name,
                "type": _filterTypesInv[irule.type],
                "domains": irule.domains,
                "priority": irule.priority,
                "wlan": irule.wlan,
            }
            for irule in rules.list()
            if irule.name in names
        ]

        MODULE.info("internetrules.get: results: %s" % (result,))
        self.finished(request.id, result)

    @sanitize(DictSanitizer({"object": StringSanitizer()}, required=True))
    def remove(self, request):
        """
        Removes the specified rules
        requests.options = [ { "object": <ruleName> }, ... ]
        """
        MODULE.info("internetrules.remove: options: %s" % (request.options,))
        result = []
        # fetch all rules with the given names
        for ientry in request.options:
            iname = ientry["object"]
            success = False
            if iname:
                success = rules.remove(iname)
            result.append({"name": iname, "success": success})

        MODULE.info("internetrules.remove: results: %s" % (result,))
        self.finished(request.id, result)

    @staticmethod
    def _parseRule(iprops, forceAllProperties=False):
        # validate types
        for ikey, itype in (
            ("name", six.string_types),
            ("type", six.string_types),
            ("priority", (int, six.string_types)),
            ("wlan", bool),
            ("domains", list),
        ):
            if ikey not in iprops:
                if forceAllProperties:
                    # raise exception as the key is not present
                    raise ValueError(_('The key "%s" has not been specified: %s') % (ikey, iprops))
                continue
            if not isinstance(iprops[ikey], itype):
                typeStr = ""
                if isinstance(itype, tuple):
                    typeStr = ", ".join(i.__name__ for i in itype)
                else:
                    typeStr = itype.__name__
                raise ValueError(_('The key "%s" needs to be of type: %s') % (ikey, typeStr))

        # validate name
        if "name" in iprops and not univention.config_registry.validate_key(iprops["name"]):
            raise ValueError(
                _(
                    'Invalid rule name "%s". The name needs to be a string, the following special '
                    "characters are not allowed: %s"
                )
                % (
                    iprops.get("name"),
                    '!, ", §, $, %, &, (, ), [, ], {, }, =, ?, `, +, #, \', ",", ;, <, >, \\',
                )
            )

        # validate type
        if "type" in iprops and iprops["type"] not in _filterTypes:
            raise ValueError(_("Filter type is unknown: %s") % iprops["type"])

        # validate domains
        if "domains" in iprops:
            parsedDomains = []
            for idomain in iprops["domains"]:

                def _validValueChar():
                    # helper function to check for invalid characters
                    return not set(idomain) & set(univention.config_registry.backend.INVALID_VALUE_CHARS)

                if not isinstance(idomain, six.string_types) or not _validValueChar():
                    raise ValueError(_("Invalid domain "))

                # parse domain
                domain = idomain
                if "://" not in domain:
                    # make sure that we have a scheme defined for parsing
                    MODULE.info("Adding a leading scheme for parsing of domain: %s" % idomain)
                    domain = "http://%s" % domain
                domain = urlparse(domain).hostname
                MODULE.info("Parsed domain: %s -> %s" % (idomain, domain))
                if not domain:
                    raise ValueError(
                        _(
                            'The specified domain "%s" is not valid. Please specify a valid domain '
                            'name, such as "wikipedia.org", "facebook.com"'
                        )
                        % idomain
                    )

                # add domain to list of parsed domains
                parsedDomains.append(domain)

            # save parsed domains in the dict
            iprops["domains"] = parsedDomains

        return iprops

    @sanitize(
        DictSanitizer(
            {
                "object": DictSanitizer(
                    {
                        "name": StringSanitizer(required=True),
                        "type": ChoicesSanitizer(list(_filterTypes.keys()), required=True),
                        "wlan": BooleanSanitizer(required=True),
                        "priority": IntegerSanitizer(required=True),
                        "domains": ListSanitizer(StringSanitizer(required=True), required=True),
                    },
                    required=True,
                )
            },
            required=True,
        )
    )
    def add(self, request):
        """
        Add the specified new rules:
        requests.options = [ {
            'object': {
                'name': <str>,
                'type': 'whitelist' | 'blacklist',
                'priority': <int> | <str>,
                'wlan': <bool>,
                'domains': [<str>, ...],
            }
        }, ... ]
        """
        # try to create all specified projects
        result = []
        for ientry in request.options:
            iprops = ientry["object"]
            try:
                # make sure that the rule does not already exist
                irule = rules.load(iprops["name"])
                if irule:
                    raise ValueError(
                        _("A rule with the same name does already exist: %s") % iprops["name"]
                    )

                # parse the properties
                parsedProps = self._parseRule(iprops, True)

                # create a new rule from the user input
                newRule = rules.Rule(
                    name=parsedProps["name"],
                    type=_filterTypes[parsedProps["type"]],
                    priority=parsedProps["priority"],
                    wlan=parsedProps["wlan"],
                    domains=parsedProps["domains"],
                )

                # try to save filter rule
                newRule.save()
                MODULE.info("Created new rule: %s" % newRule)

                # everything ok
                result.append({"name": iprops["name"], "success": True})
            except (ValueError, KeyError) as e:
                # data not valid... create error info
                MODULE.info(
                    'data for internet filter rule "%s" is not valid: %s' % (iprops.get("name"), e)
                )
                result.append({"name": iprops.get("name"), "success": False, "details": str(e)})

        # return the results
        self.finished(request.id, result)

    @sanitize(
        DictSanitizer(
            {
                "object": DictSanitizer(
                    {
                        "name": StringSanitizer(required=True),
                        "type": ChoicesSanitizer(list(_filterTypes.keys()), required=True),
                        "wlan": BooleanSanitizer(required=True),
                        "priority": IntegerSanitizer(required=True),
                        "domains": ListSanitizer(StringSanitizer(required=True), required=True),
                    },
                    required=True,
                ),
                "options": DictSanitizer({"name": StringSanitizer()}, required=True),
            },
            required=True,
        )
    )
    def put(self, request):
        """
        Modify an existing rule:

        requests.options = [ {
            'object': {
                'name': <str>,                      # optional
                'type': 'whitelist' | 'blacklist',  # optional
                'priority': <int>,                  # optional
                'wlan': <bool>,                     # optional
                'domains': [<str>, ...],            # optional
            },
            'options': {
                'name': <str>  # the original name of the object
            }
        }, ... ]
        """
        # try to create all specified projects
        result = []
        for ientry in request.options:
            try:
                # get properties and options from entry
                iprops = ientry["object"]
                iname = None
                ioptions = ientry.get("options")
                if ioptions:
                    iname = ioptions.get("name")
                if not iname:
                    raise ValueError(_('No "name" attribute has been specified in the options.'))

                # make sure that the rule already exists
                irule = rules.load(iname)
                if not irule:
                    raise ValueError(
                        _("The rule does not exist and cannot be modified: %s") % iprops.get("name", "")
                    )

                # parse the properties
                self._parseRule(iprops)

                if iprops.get("name", iname) != iname:
                    # name has been changed -> remove old rule and create a new one
                    rules.remove(iname)
                    irule.name = iprops["name"]

                if "type" in iprops:
                    # set rule type, move all domains from the previous type
                    oldDomains = irule.domains
                    irule.domains = []
                    irule.type = _filterTypes[iprops["type"]]
                    irule.domains = oldDomains

                if "priority" in iprops:
                    # set priority
                    irule.priority = iprops["priority"]

                if "wlan" in iprops:
                    # set wlan
                    irule.wlan = iprops["wlan"]

                if "domains" in iprops:
                    # set domains
                    irule.domains = iprops["domains"]

                # try to save filter rule
                irule.save()
                MODULE.info("Saved rule: %s" % irule)

                # everything ok
                result.append({"name": iname, "success": True})
            except ValueError as e:
                # data not valid... create error info
                MODULE.info(
                    'data for internet filter rule "%s" is not valid: %s' % (iprops.get("name"), e)
                )
                result.append({"name": iprops.get("name"), "success": False, "details": str(e)})

        # return the results
        self.finished(request.id, result)

    @sanitize(
        school=SchoolSanitizer(required=True),
        pattern=LDAPSearchSanitizer(required=False, default="", use_asterisks=True, add_asterisks=False),
    )
    @LDAP_Connection()
    def groups_query(self, request, ldap_user_read=None, ldap_position=None):
        """List all groups (classes, workgroups) and their assigned internet rule"""
        school = request.options["school"]
        pattern = LDAP_Filter.forAll(
            request.options.get("pattern", ""),
            ["name", "description"],
            _escape_filter_chars=False,
            school_prefix=school,
        )
        pattern_with_school_suffix = LDAP_Filter.forAll(
            request.options.get("pattern", ""),
            ["name", "description"],
            _escape_filter_chars=False,
            school_suffix=school,
        )
        pattern_with_space_school_suffix = LDAP_Filter.forAll(
            request.options.get("pattern", ""),
            ["name", "description"],
            _escape_filter_chars=False,
            school_suffix=school,
            seperator=" ",  # For the case: Domain Users <OU> and possibly others?
        )

        # Bug #55034: In case values in ucsschool/ldap/default/groupprefix/*
        # are changed and do not end with a space or "-".
        pattern_with_school_suffix_without_separator = LDAP_Filter.forAll(
            request.options.get("pattern", ""),
            ["name", "description"],
            _escape_filter_chars=False,
            school_suffix=school,
            seperator="",
        )

        groups = [
            x
            for x in Group.get_all(
                ldap_user_read,
                school,
                "(|{}{}{}{})".format(
                    pattern,
                    pattern_with_school_suffix,
                    pattern_with_space_school_suffix,
                    pattern_with_school_suffix_without_separator,
                ),
            )
            if not x.self_is_computerroom()
        ]
        internet_rules = rules.getGroupRuleName([i.name for i in groups])
        name = re.compile("-%s$" % (re.escape(school)), flags=re.I)
        result = [
            {
                "name": i.get_relative_name()
                if hasattr(i, "get_relative_name")
                else name.sub("", i.name),
                "$dn$": i.dn,
                "rule": internet_rules.get(i.name, "default") or "$default$",
            }
            for i in groups
        ]
        result.sort(key=lambda x: x["name"])
        self.finished(request.id, result)

    @sanitize(
        DictSanitizer({"group": StringSanitizer(required=True), "rule": StringSanitizer(required=True)})
    )
    @LDAP_Connection()
    def groups_assign(self, request, ldap_user_read=None, ldap_position=None):
        """
        Assigns default rules to groups:
        request.options = [ { 'group': <groupDN>, 'rule': <ruleName> }, ... ]
        """
        MODULE.info("internetrules.groups_assign: options: %s" % str(request.options))

        # try to load all group rules
        newRules = {}
        rmRules = []
        for ientry in request.options:
            # make sure the group exists
            igrp = udm_objects.get(
                udm_modules.get("groups/group"), None, ldap_user_read, ldap_position, ientry["group"]
            )
            if not igrp:
                raise UMC_Error("unknown group object")
            igrp.open()

            # check the rule name
            irule = ientry["rule"]
            if irule == "$default$":
                # remove the rule
                rmRules.append(igrp["name"])
            else:
                try:
                    # make sure the rule name is valid
                    self._parseRule({"name": irule})
                except ValueError as exc:
                    raise UMC_Error(str(exc))

                # add new rule
                newRules[igrp["name"]] = irule

        # assign default filter rules to groups
        rules.setGroupRuleName(newRules)
        rules.unsetGroupRuleName(rmRules)

        MODULE.info("internetrules.groups_assign: finished")
        self.finished(request.id, True)
