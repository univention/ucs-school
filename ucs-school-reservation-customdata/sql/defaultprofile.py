#/usr/bin/python2.4
#
# Univention UCS@School
#
# Copyright (C) 2007-2009 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# Binary versions of this file provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import MySQLdb
import csv
AdminUserUID = 0

f=open("/etc/reservation-sql.secret")
password=f.readline().rstrip()
f.close()
db=MySQLdb.connect(db="reservation", user="reservation", passwd=password )
if db.get_server_info() >= '4.1' and not db.character_set_name().startswith('utf8'):
	db.set_character_set('utf8')
cursor=db.cursor()

### 1. remove profoptrel record referencing a default profile
cursor.execute("""DELETE FROM profoptrel USING profoptrel INNER JOIN resprofiles WHERE profoptrel.resprofileID = resprofiles.resprofileID AND resprofiles.isglobaldefault = True""")
### 2. remove default profiles
cursor.execute("""DELETE FROM resprofiles WHERE isglobaldefault = True""")
### 3. insert default profiles letting resprofileID being determined by autoincrement
## first read default_profoptrel
g=open('/usr/share/ucs-school-reservation-customdata/default_profoptrel.csv', "rb")
import_profoptrel={}
for row in csv.reader(g, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", doublequote=False):	## read records and store them sorted by resprofileID
	if row[0].startswith('#'):
		continue
	if not len(row) == 3:
		print "default_profoptrel.csv: Format error, skipping Line: %s" % row

	resprofileNumber = row[1]
	if not resprofileNumber in import_profoptrel:
		import_profoptrel[ resprofileNumber ] = []
	import_profoptrel[ resprofileNumber ].append( [ row[0], row[2] ] )
g.close()
## insert each record and determine the ID it was given by autoincrement.
f=open('/usr/share/ucs-school-reservation-customdata/default_resprofiles.csv', "rb")
for row in csv.reader(f, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", doublequote=False):
	if row[0].startswith('#'):
		continue
	if not len(row) == 3:
		print "default_resprofiles.csv: Format error, skipping Line: %s" % row

	resprofileNumber=row[0]
	cursor.execute("""INSERT INTO resprofiles (name, description, owner, isglobaldefault)
		VALUES (%s, %s, %s, %s)""",
		(row[1], row[2], AdminUserUID, 1)
		)
	## determine the fresh ID
	cursor.execute("""SELECT resprofileID FROM resprofiles
			WHERE name=%s AND isglobaldefault=True""", row[1])
	resprofileID=cursor.fetchone()

	### 4. insert corresponding profoptrel records, translating resprofileNumber into resprofileID
	for element in import_profoptrel[resprofileNumber]:
		cursor.execute("""INSERT INTO profoptrel (ressettingID, resprofileID, value)
		VALUES (%s, %s, %s)""",
		(element[0], resprofileID[0], element[1])
		)
f.close()

### 5. load default_ressettings into ressettings table, numbering is static, replacing duplicate entries.
cursor.execute("""LOAD DATA INFILE '/usr/share/ucs-school-reservation-customdata/default_ressettings.csv'
  REPLACE
  INTO TABLE ressettings
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
  LINES TERMINATED BY '\n'""")

db.close()
