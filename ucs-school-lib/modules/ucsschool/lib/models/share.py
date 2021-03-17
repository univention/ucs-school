# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2021 Univention GmbH
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
from typing import List, Optional, Type

from ldap.filter import filter_format
from six import iteritems

from udm_rest_client import UDM, NoObject as UdmNoObject, UdmObject
from univention.admin.uldap import getMachineConnection
from univention.lib.misc import custom_groupname

from ..roles import role_marketplace_share, role_school_class_share, role_workgroup_share
from .attributes import SchoolClassAttribute, ShareName, WorkgroupAttribute
from .base import (
    RoleSupportMixin,
    SuperOrdinateType,
    UCSSchoolHelperAbstractClass,
    UCSSchoolModel,
    WrongObjectType,
)
from .utils import _, ucr


class NoSID(Exception):
    pass


class NoSchoolGroup(Exception):
    pass


class SetNTACLsMixin(object):
    """
    Mixin for setting NTACLs of UCS@school Share (sub)classes. For example to
    to prevent students from changing the permissions in a share (Bug #42182).

    D ~ deny, OI/ OBJECT_INHERIT_ACE ~ Object inheritance, CI/ CONTAINER_INHERIT_ACE ~ container
    inheritance
    RC/ READ_CONTROL ~ display security attributes WO/ WRITE_OWNER ~ take ownership
    WD/ WRITE_DAC ~ write security permissions
    To make sure, students can edit folders&files in subfolders, they need to inherit edit
    or full control, since they are denied first.
    For a complete overview of all options, see
    https://docs.microsoft.com/en-us/windows/win32/secauthz/ace-strings
    """

    def get_nt_acls(self, lo: UDM) -> List[str]:
        return []

    @staticmethod
    def get_groups_samba_sid(lo: UDM, dn: str) -> str:
        ldap_lo, ldap_po = getMachineConnection()
        try:
            return ldap_lo.get(dn)["sambaSID"][0]  # TODO
        except (IndexError, KeyError):
            raise NoSID("Group {!r} has no/empty 'sambaSID' attribute.".format(dn))

    def get_ou_admin_full_control(self, lo: UDM) -> List[str]:
        admin_dn = "cn=admins-{},cn=ouadmins,cn=groups,{}".format(
            self.school.lower(), ucr.get("ldap/base")
        )
        samba_sid = self.get_groups_samba_sid(lo, admin_dn)
        return ["(A;OICI;0x001f01ff;;;{})".format(samba_sid)]

    def get_aces_deny_students_change_permissions(self, lo: UDM) -> List[str]:
        """
        Get the schueler-ou sid to deny all students the
        permissions to modify permissions and take ownership.
        Derived classes may add more NTACLS.

        Sets NT ACLs to disallow students to deny students to change the permission of
        folders, subfolder and files or to take ownership of them as well as
        displaying them (RC).
        """
        search_base = self.get_search_base(self.school)
        student_group_dn = "cn={}{},cn=groups,{}".format(
            search_base.group_prefix_students, self.school, search_base.schoolDN
        )
        samba_sid = self.get_groups_samba_sid(lo, student_group_dn)
        return ["(D;OICI;WOWD;;;{})".format(samba_sid)]

    def get_aces_work_group(self, lo: UDM) -> List[str]:
        """
        ACE: deny schueler to change permissions & take ownership
        ACE: allow workgroup-members to read/write/modify
        ACE: allow ou-admins full control
        """
        res = self.get_aces_deny_students_change_permissions(lo)
        if self.school_group:
            group_dn = self.school_group.dn
        else:
            raise NoSchoolGroup("No schoolgroup set.")
        samba_sid = self.get_groups_samba_sid(lo, group_dn)
        res.append("(A;OICI;0x001f01ff;;;{})".format(samba_sid))
        res.extend(self.get_ou_admin_full_control(lo))
        return res

    def get_aces_market_place(self, lo: UDM) -> List[str]:
        """
        ACE: deny schueler to change permissions & take ownership
        ACE: allow Domain Users to read/write/modify
        ACE: allow ou-admins full control
        """
        res = self.get_aces_deny_students_change_permissions(lo)
        search_base = self.get_search_base(self.school)
        domain_users_dn = "cn=Domain Users %s,%s" % (self.school.lower(), search_base.groups)
        samba_sid = self.get_groups_samba_sid(lo, domain_users_dn)
        res.append("(A;OICI;0x001f01ff;;;{})".format(samba_sid))
        res.extend(self.get_ou_admin_full_control(lo))
        return res

    def get_aces_class_group(self, lo: UDM) -> List[str]:
        """
        ACE: deny schueler to change permissions & take ownership
        ACE: allow class-members to read/write/modify
        ACE: allow ou-admins full control
        """
        res = self.get_aces_deny_students_change_permissions(lo)
        if self.school_group:
            group_dn = self.school_group.dn
        else:
            raise NoSchoolGroup("No schoolgroup set.")
        samba_sid = self.get_groups_samba_sid(lo, group_dn)
        res.append("(A;OICI;0x001f01ff;;;{})".format(samba_sid))
        res.extend(self.get_ou_admin_full_control(lo))
        return res

    def set_nt_acls(self, udm_obj: UdmObject, lo: UDM) -> None:
        try:
            udm_obj.props.appendACL = self.get_nt_acls(lo)
        except NoSID as exc:
            self.logger.warning("Not setting NTACLs for %s: %s", self.__class__.__name__, exc)
            return
        udm_obj.props.sambaInheritOwner = True
        udm_obj.props.sambaInheritPermissions = True


class Share(UCSSchoolHelperAbstractClass):
    name: str = ShareName(_("Name"))

    create_defaults = {
        "writeable": True,
        "sambaWriteable": True,
        "sambaBrowseable": True,
        "sambaForceGroup": "+{name}",
        "sambaCreateMode": "0770",
        "sambaDirectoryMode": "0770",
        "owner": 0,
        "group": 0,
        "directorymode": "0770",
    }
    paths = {
        "no_roleshare": "/home/groups/{name}",
        "roleshare": "/home/{ou}/groups/{name}",
    }

    @classmethod
    def get_container(cls, school: str) -> str:
        return cls.get_search_base(school).shares

    async def do_create(self, udm_obj: UdmObject, lo: UDM) -> None:
        for k, v in iteritems(self.create_defaults):
            setattr(udm_obj.props, k, v)
        udm_obj.props.host = await self.get_server_fqdn(lo)
        udm_obj.props.path = self.get_share_path()
        try:
            udm_obj.props.sambaForceGroup = self.create_defaults["sambaForceGroup"].format(
                name=self.name
            )
        except KeyError:
            # MarketplaceShare doesn't set this
            pass
        udm_obj.props.group = await self.get_gid_number(lo)
        if ucr.is_false("ucsschool/default/share/nfs", True):
            try:
                udm_obj.options["nfs"] = False  # deactivate NFS
            except ValueError:
                pass
        self.logger.info('Creating share on "%s"', udm_obj.props.host)
        return await super(Share, self).do_create(udm_obj, lo)

    async def get_gid_number(self, lo: UDM) -> str:
        raise NotImplementedError()

    def get_share_path(self, school: str = None) -> str:
        school = school or self.school
        if ucr.is_true("ucsschool/import/roleshare", True):
            path_template = self.paths["roleshare"]
        else:
            path_template = self.paths["no_roleshare"]
        return path_template.format(ou=school, name=self.name)

    async def do_modify(self, udm_obj: UdmObject, lo: UDM) -> None:
        old_name = self.get_name_from_dn(self.old_dn)
        if old_name != self.name:
            head, tail = os.path.split(udm_obj.props.path)
            tail = self.name
            udm_obj.props.path = os.path.join(head, tail)
            if udm_obj.props.sambaName == old_name:
                udm_obj.props.sambaName = self.name
            if udm_obj.props.sambaForceGroup == "+%s" % old_name:
                udm_obj.props.sambaForceGroup = "+%s" % self.name
        return await super(Share, self).do_modify(udm_obj, lo)

    @staticmethod
    async def get_server_udm_object(dn: str, lo: UDM) -> Optional[UdmObject]:
        mod = lo.get("computers/domaincontroller_slave")
        try:
            return await mod.get(dn)
        except UdmNoObject:
            pass
        mod = lo.get("computers/domaincontroller_master")
        try:
            return await mod.get(dn)
        except UdmNoObject:
            return None

    async def get_server_fqdn(self, lo: UDM) -> Optional[str]:
        domainname = ucr.get("domainname")
        school = await self.get_school_obj(lo)
        school_dn = school.dn

        # fetch serverfqdn from OU
        # TODO: change this also in 4.4
        from .school import School

        school: School = await School.from_dn(school_dn, None, lo)
        school_udm_obj = await school.get_udm_object(lo)
        class_share_file_server_dn: str = school_udm_obj.props.ucsschoolClassShareFileServer
        if class_share_file_server_dn:
            server_udm = await self.get_server_udm_object(class_share_file_server_dn, lo)
            server_domain_name = server_udm.props.domain
            if not server_domain_name:
                server_domain_name = domainname
            result = server_udm.props.name
            if result:
                return "%s.%s" % (result, server_domain_name)

        # get alternative server (defined at ou object if a dc slave is responsible for more than one ou)
        ldap_lo, ldap_po = getMachineConnection()
        ou_attr_ldap_access_write = ldap_lo.get(school_dn, ["univentionLDAPAccessWrite"])
        alternative_server_dn = None
        if len(ou_attr_ldap_access_write) > 0:
            alternative_server_dn = ou_attr_ldap_access_write["univentionLDAPAccessWrite"][0]
            if len(ou_attr_ldap_access_write) > 1:
                self.logger.warning(
                    "more than one corresponding univentionLDAPAccessWrite found at ou=%s", self.school
                )

        # build fqdn of alternative server and set serverfqdn
        if alternative_server_dn:
            alternative_server_attr = ldap_lo.get(alternative_server_dn, ["uid"])
            if len(alternative_server_attr) > 0:
                alternative_server_uid = alternative_server_attr["uid"][0]
                alternative_server_uid = alternative_server_uid.replace("$", "")
                if len(alternative_server_uid) > 0:
                    return "%s.%s" % (alternative_server_uid, domainname)

        # fallback
        return "%s.%s" % (school.get_dc_name_fallback(), domainname)

    class Meta:
        udm_module = "shares/share"


class GroupShare(SetNTACLsMixin, Share):
    school_group = SchoolClassAttribute(_("School class"), required=True, internal=True)

    @classmethod
    def from_school_group(cls, school_group: UCSSchoolModel) -> "GroupShare":
        from .group import Group  # isort:skip  # prevent cyclic import

        if not isinstance(school_group, Group):
            raise WrongObjectType(dn=getattr(school_group, "dn", "<no 'dn' attribute>"), cls=Group)
        return cls(name=school_group.name, school=school_group.school, school_group=school_group)

    from_school_class = from_school_group  # legacy

    async def get_gid_number(self, lo: UDM) -> str:
        return (await self.school_group.get_udm_object(lo)).props.gidNumber

    def get_share_path(self, school=None) -> str:
        school = school or self.school_group.school
        return super(GroupShare, self).get_share_path(school)

    async def do_create(self, udm_obj, lo) -> None:
        self.set_nt_acls(udm_obj, lo)
        return await super(GroupShare, self).do_create(udm_obj, lo)


class WorkGroupShare(RoleSupportMixin, GroupShare):
    school_group = WorkgroupAttribute(_("Work group"), required=True, internal=True)
    default_roles = [role_workgroup_share]
    _school_in_name_prefix = True

    @classmethod
    def get_container(cls, school) -> str:
        return cls.get_search_base(school).shares

    @classmethod
    async def get_all(
        cls,
        lo: UDM,
        school: str = None,
        filter_str: str = None,
        easy_filter: str = False,
        superordinate: SuperOrdinateType = None,
    ) -> List[UCSSchoolModel]:
        """
        This method was overwritten to identify WorkGroupShares and distinct them
        from other shares of the school.
        If at some point a lookup is implemented that uses the role attribute
        which is reliable this code can be removed.
        Bug #48428
        """
        shares = await super(WorkGroupShare, cls).get_all(
            lo, school, filter_str, easy_filter, superordinate
        )
        filtered_shares = []
        search_base = cls.get_search_base(school)
        grp_mod = lo.get("groups/group")
        for share in shares:
            filter_s = filter_format("name=%s", (share.name,))
            async for group in grp_mod.search(filter_s, base=search_base.groups):
                if search_base.isWorkgroup(group.dn):
                    filtered_shares.append(share)
        return filtered_shares

    def get_nt_acls(self, lo: UDM) -> List[str]:
        return self.get_aces_work_group(lo)


class ClassShare(RoleSupportMixin, GroupShare):
    school_group = SchoolClassAttribute(_("School class"), required=True, internal=True)
    default_roles = [role_school_class_share]
    _school_in_name_prefix = True
    paths = {
        "no_roleshare": "/home/groups/klassen/{name}",
        "roleshare": "/home/{ou}/groups/klassen/{name}",
    }

    @classmethod
    def get_container(cls, school) -> str:
        return cls.get_search_base(school).classShares

    @classmethod
    def get_group_class(cls) -> Type["ClassShare"]:
        # prevent import loop
        from .group import ClassShare  # isort:skip

        return ClassShare

    def get_nt_acls(self, lo: UDM) -> List[str]:
        return self.get_aces_class_group(lo)


class MarketplaceShare(RoleSupportMixin, SetNTACLsMixin, Share):
    default_roles = [role_marketplace_share]
    _school_in_name_prefix = False

    def __init__(self, name: str = "Marktplatz", school: str = None, **kwargs) -> None:
        if name != "Marktplatz":
            raise ValueError("Name of market place must be 'Marktplatz'.")
        super(MarketplaceShare, self).__init__(name, school, **kwargs)

    @classmethod
    def get_container(cls, school) -> str:
        return cls.get_search_base(school).shares

    @classmethod
    async def get_all(
        cls,
        lo: UDM,
        school: str = None,
        filter_str: str = None,
        easy_filter: str = False,
        superordinate: SuperOrdinateType = None,
    ) -> List["MarketplaceShare"]:
        # ignore all filter arguments, there is only one Marktplatz share per school
        return await super(MarketplaceShare, cls).get_all(lo, school, filter_str="cn=Marktplatz")

    async def get_gid_number(self, lo: UDM) -> str:
        group_name = ucr.get("ucsschool/import/generate/share/marktplatz/group") or custom_groupname(
            "Domain Users"
        )
        group_entry = grp.getgrnam(group_name)
        return str(group_entry.gr_gid)

    def get_share_path(self, school: str = None) -> str:
        path = ucr.get("ucsschool/import/generate/share/marktplatz/sharepath")
        if path:
            return path
        else:
            school = school or self.school
            return super(MarketplaceShare, self).get_share_path(school)

    async def do_create(self, udm_obj: UdmObject, lo: UDM) -> None:
        self.create_defaults["directorymode"] = (
            ucr.get("ucsschool/import/generate/share/marktplatz/permissions") or "0777"
        )
        self.create_defaults.pop("sambaForceGroup", None)
        self.create_defaults.pop("sambaCreateMode", None)
        self.create_defaults.pop("sambaDirectoryMode", None)
        self.set_nt_acls(udm_obj, lo)
        return await super(MarketplaceShare, self).do_create(udm_obj, lo)

    def get_nt_acls(self, lo: UDM) -> List[str]:
        return self.get_aces_market_place(lo)

    class Meta(Share.Meta):
        udm_filter = "(&(univentionObjectType=shares/share)(cn=Marktplatz))"
