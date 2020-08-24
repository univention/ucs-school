# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2020 Univention GmbH
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

import grp
import os.path

from ldap.filter import filter_format
from six import iteritems

from univention.lib.misc import custom_groupname
from univention.udm import UDM

from ..roles import role_marketplace_share, role_school_class_share, role_workgroup_share
from .attributes import Roles, SchoolClassAttribute, ShareName, WorkgroupAttribute
from .base import RoleSupportMixin, UCSSchoolHelperAbstractClass
from .utils import _, ucr

try:
    from typing import Any, Optional
except ImportError:
    pass


class Share(UCSSchoolHelperAbstractClass):
    name = ShareName(_("Name"))

    create_defaults = {
        "writeable": "1",
        "sambaWriteable": "1",
        "sambaBrowseable": "1",
        "sambaForceGroup": "+{name}",
        "sambaCreateMode": "0770",
        "sambaDirectoryMode": "0770",
        "owner": "0",
        "group": "0",
        "directorymode": "0770",
    }
    paths = {
        "no_roleshare": "/home/groups/{name}",
        "roleshare": "/home/{ou}/groups/{name}",
    }

    @classmethod
    def get_container(cls, school):
        return cls.get_search_base(school).shares

    def do_create(self, udm_obj, lo):
        for k, v in iteritems(self.create_defaults):
            udm_obj[k] = v
        udm_obj["host"] = self.get_server_fqdn(lo)
        udm_obj["path"] = self.get_share_path()
        udm_obj["sambaForceGroup"] = self.create_defaults["sambaForceGroup"].format(name=self.name)
        udm_obj["group"] = self.get_gid_number(lo)
        if ucr.is_false("ucsschool/default/share/nfs", True):
            try:
                udm_obj.options.remove("nfs")  # deactivate NFS
            except ValueError:
                pass
        self.logger.info('Creating share on "%s"', udm_obj["host"])
        return super(Share, self).do_create(udm_obj, lo)

    def get_gid_number(self, lo):
        raise NotImplementedError()

    def get_share_path(self, school=None):
        school = school or self.school
        if ucr.is_true("ucsschool/import/roleshare", True):
            path_template = self.paths["roleshare"]
        else:
            path_template = self.paths["no_roleshare"]
        return path_template.format(ou=school, name=self.name)

    def do_modify(self, udm_obj, lo):
        old_name = self.get_name_from_dn(self.old_dn)
        if old_name != self.name:
            head, tail = os.path.split(udm_obj["path"])
            tail = self.name
            udm_obj["path"] = os.path.join(head, tail)
            if udm_obj["sambaName"] == old_name:
                udm_obj["sambaName"] = self.name
            if udm_obj["sambaForceGroup"] == "+%s" % old_name:
                udm_obj["sambaForceGroup"] = "+%s" % self.name
        return super(Share, self).do_modify(udm_obj, lo)

    def get_server_fqdn(self, lo):
        domainname = ucr.get("domainname")
        school = self.get_school_obj(lo)
        school_dn = school.dn

        # fetch serverfqdn from OU
        result = lo.get(school_dn, ["ucsschoolClassShareFileServer"])
        if result:
            server_domain_name = lo.get(result["ucsschoolClassShareFileServer"][0], ["associatedDomain"])
            if server_domain_name:
                server_domain_name = server_domain_name["associatedDomain"][0]
            else:
                server_domain_name = domainname
            result = lo.get(result["ucsschoolClassShareFileServer"][0], ["cn"])
            if result:
                return "%s.%s" % (result["cn"][0], server_domain_name)

        # get alternative server (defined at ou object if a dc slave is responsible for more than one ou)
        ou_attr_ldap_access_write = lo.get(school_dn, ["univentionLDAPAccessWrite"])
        alternative_server_dn = None
        if len(ou_attr_ldap_access_write) > 0:
            alternative_server_dn = ou_attr_ldap_access_write["univentionLDAPAccessWrite"][0]
            if len(ou_attr_ldap_access_write) > 1:
                self.logger.warning(
                    "more than one corresponding univentionLDAPAccessWrite found at ou=%s", self.school
                )

        # build fqdn of alternative server and set serverfqdn
        if alternative_server_dn:
            alternative_server_attr = lo.get(alternative_server_dn, ["uid"])
            if len(alternative_server_attr) > 0:
                alternative_server_uid = alternative_server_attr["uid"][0]
                alternative_server_uid = alternative_server_uid.replace("$", "")
                if len(alternative_server_uid) > 0:
                    return "%s.%s" % (alternative_server_uid, domainname)

        # fallback
        return "%s.%s" % (school.get_dc_name_fallback(), domainname)

    class Meta:
        udm_module = "shares/share"


class GroupShare(Share):
    school_group = SchoolClassAttribute(_("School class"), required=True, internal=True)

    @classmethod
    def from_school_group(cls, school_group):
        return cls(name=school_group.name, school=school_group.school, school_group=school_group)

    from_school_class = from_school_group  # legacy

    def get_gid_number(self, lo):
        return self.school_group.get_udm_object(lo)["gidNumber"]

    def get_share_path(self, school=None):
        school = school or self.school_group.school
        return super(GroupShare, self).get_share_path(school)


class WorkGroupShare(RoleSupportMixin, GroupShare):
    school_group = WorkgroupAttribute(_("Work group"), required=True, internal=True)
    ucsschool_roles = Roles(_("Roles"), aka=["Roles"])
    default_roles = [role_workgroup_share]
    _school_in_name_prefix = True

    @classmethod
    def get_container(cls, school):
        return cls.get_search_base(school).shares

    @classmethod
    def get_all(cls, lo, school, filter_str=None, easy_filter=False, superordinate=None):
        """
        This method was overwritten to identify WorkGroupShares and distinct them
        from other shares of the school.
        If at some point a lookup is implemented that uses the role attribute
        which is reliable this code can be removed.
        Bug #48428
        """
        shares = super(WorkGroupShare, cls).get_all(lo, school, filter_str, easy_filter, superordinate)
        filtered_shares = []
        search_base = cls.get_search_base(school)
        for share in shares:
            groups = (
                UDM(lo)
                .version(1)
                .get("groups/group")
                .search(filter_format("name=%s", [share.name]), base=search_base.groups)
            )
            if any((search_base.isWorkgroup(g.dn) for g in groups)):
                filtered_shares.append(share)
        return filtered_shares


class ClassShare(RoleSupportMixin, GroupShare):
    school_group = SchoolClassAttribute(_("School class"), required=True, internal=True)
    ucsschool_roles = Roles(_("Roles"), aka=["Roles"])
    default_roles = [role_school_class_share]
    _school_in_name_prefix = True
    paths = {
        "no_roleshare": "/home/groups/klassen/{name}",
        "roleshare": "/home/{ou}/groups/klassen/{name}",
    }

    @classmethod
    def get_container(cls, school):
        return cls.get_search_base(school).classShares

    @classmethod
    def get_group_class(cls):
        # prevent import loop
        from .group import ClassShare  # isort:skip

        return ClassShare


class MarketplaceShare(RoleSupportMixin, Share):
    ucsschool_roles = Roles(_("Roles"), aka=["Roles"])
    default_roles = [role_marketplace_share]
    _school_in_name_prefix = False

    def __init__(
        self, name="Marktplatz", school=None, **kwargs
    ):  # type: (Optional[str], Optional[str], **Any) -> None
        if name != "Marktplatz":
            raise ValueError("Name of market place must be 'Marktplatz'.")
        super(MarketplaceShare, self).__init__(name, school, **kwargs)

    @classmethod
    def get_container(cls, school):
        return cls.get_search_base(school).shares

    @classmethod
    def get_all(cls, lo, school, filter_str=None, easy_filter=False, superordinate=None):
        # ignore all filter arguments, there is only one Marktplatz share per school
        return super(MarketplaceShare, cls).get_all(lo, school, filter_str="cn=Marktplatz")

    def get_gid_number(self, lo):
        group_name = ucr.get("ucsschool/import/generate/share/marktplatz/group") or custom_groupname(
            "Domain Users"
        )
        group_entry = grp.getgrnam(group_name)
        return str(group_entry.gr_gid)

    def get_share_path(self, school=None):
        path = ucr.get("ucsschool/import/generate/share/marktplatz/sharepath")
        if path:
            return path
        else:
            school = school or self.school
            return super(MarketplaceShare, self).get_share_path(school)

    def do_create(self, udm_obj, lo):
        self.create_defaults["directorymode"] = (
            ucr.get("ucsschool/import/generate/share/marktplatz/permissions") or "0777"
        )
        return super(MarketplaceShare, self).do_create(udm_obj, lo)
