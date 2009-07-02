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
g=open('/usr/share/univention-reservation-customdata/default_profoptrel.csv', "rb")
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
f=open('/usr/share/univention-reservation-customdata/default_resprofiles.csv', "rb")
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
cursor.execute("""LOAD DATA INFILE '/usr/share/univention-reservation-customdata/default_ressettings.csv'
  REPLACE
  INTO TABLE ressettings
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
  LINES TERMINATED BY '\n'""")

db.close()
