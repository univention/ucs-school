#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school RADIUS 802.1X
#  NTLM-Authentication program
#
# SPDX-FileCopyrightText: 2012-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only


from univention.radius.networkaccess import NetworkAccess


class SchoolNetworkAccess(NetworkAccess):
    def __init__(self, *args, **kwargs):
        super(SchoolNetworkAccess, self).__init__(*args, **kwargs)

        self.user_to_group = {}  # { "user_lowercase": ["group1", "group2", ], }
        self.group_info = {}  # { "group1": (23, True, ), }
        self.log_target = None
        self.load_info()

    def load_info(self):
        self.logger.debug("Loading proxy rules from UCR")
        for key in self.configRegistry:
            if key.startswith("proxy/filter/usergroup/"):
                group = key[len("proxy/filter/usergroup/") :]
                users = self.configRegistry[key].split(",")
                for user in users:
                    self.user_to_group.setdefault(user.lower(), []).append(group)
            elif key.startswith("proxy/filter/groupdefault/"):
                group = key[len("proxy/filter/groupdefault/") :]
                rule = self.configRegistry[key]
                priority = 0
                try:
                    priority = int(
                        self.configRegistry.get("proxy/filter/setting/%s/priority" % (rule,), "")
                    )
                except ValueError:
                    pass
                wlan_enabled = self.configRegistry.is_true("proxy/filter/setting/%s/wlan" % (rule,))
                if wlan_enabled is not None:
                    self.group_info[group] = (
                        priority,
                        wlan_enabled,
                    )
        self.logger.debug("Loaded user_to_group {}".format(self.user_to_group))
        self.logger.debug("Loaded group_info {}".format(self.group_info))

    def check_proxy_filter_policy(self):
        self.logger.debug("Checking UCR proxy rules for user")
        access = self.evaluate_proxy_network_access(self.username)
        if access:
            self.logger.info("Login attempt permitted by UCR proxy rules")
        else:
            self.logger.info("Login attempt denied by UCR proxy rules")
        return access

    def evaluate_proxy_network_access(self, username):
        groups = self.user_to_group.get(username.lower())
        if groups is None:
            self.logger.debug("DENY: No proxy rules for user {} found".format(username))
            return False
        matching_groups = {group: info for group, info in self.group_info.items() if group in groups}
        if not matching_groups:
            self.logger.debug("DENY: user {} not found in any WLAN enabled group".format(username))
            self.logger.debug("DENY: user {} groups={}".format(username, groups))
            self.logger.debug("DENY: WLAN enabled groups={}".format(list(self.group_info.keys())))
            return False
        max_priority = max(rule[0] for rule in matching_groups.values())
        max_priority_groups = {
            group: info for group, info in matching_groups.items() if info[0] == max_priority
        }
        if any(wlan_enabled for priority, wlan_enabled in max_priority_groups.values()):
            self.logger.debug(
                "ALLOW: WLAN is enabled in a group with highest priority (maxPriorityGroups={})".format(
                    max_priority_groups
                )
            )
            return True
        self.logger.debug(
            "DENY: WLAN is not enabled in any group with highest priority (maxPriorityGroups={})".format(
                max_priority_groups
            )
        )
        return False
