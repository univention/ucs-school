#!/usr/bin/python2.6
# -*- coding: iso-8859-15 -*-
#
# UCS@school lib
#  module: UCS@school i18n
#
# Copyright 2014 Univention GmbH
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

from ucsschool.lib.roles import role_pupil, role_teacher, role_staff

ucs_school_l10n_languages_de = {
	role_pupil:	'schueler',
	role_teacher:	'lehrer',
	role_staff:	'mitarbeiter',
	}

ucs_school_l10n_languages = {
	'de' : ucs_school_l10n_languages_de,
}

def ucs_school_name_i18n(name, lang='de'):
	'''i18n function for localization of UCS@school standard names'''

	# return _(name)		## this would be simple..
	if lang in ucs_school_l10n_languages:
		return ucs_school_l10n_languages[lang].get(name, name)
	else:
		return name

