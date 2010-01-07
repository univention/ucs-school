# Documentation:
# Create Table syntax:
# http://dev.mysql.com/doc/refman/5.1/de/create-table.html
# Datatypes
# http://dev.mysql.com/doc/refman/5.1/de/numeric-types.html

USE reservation;

######################################
# Table reservation
######################################

CREATE TABLE IF NOT EXISTS reservation (
	reservationID 		INT UNSIGNED AUTO_INCREMENT,
	name				VARCHAR(255) NOT NULL,
	description 		VARCHAR(1023),
	owner 				INT UNSIGNED,
	hostgroup 			INT UNSIGNED,
	usergroup 			INT UNSIGNED,
	startTime 			DATETIME,
	endTime 			DATETIME,
	iterationDays 		INT UNSIGNED,
	iterationEnd		DATETIME,
	iterateInVacations	BOOLEAN,
	resprofileID 		INT UNSIGNED,
	status 				VARCHAR(255) NOT NULL,
	replacedByID 		INT UNSIGNED,
	deleteFlag			BOOLEAN,

	PRIMARY KEY (reservationID)
);

CREATE INDEX reservationID_idx on reservation(reservationID);
CREATE INDEX name_idx on reservation(name);
CREATE INDEX owner_idx on reservation(owner);
CREATE INDEX startTime_idx on reservation(startTime);
CREATE INDEX endTime_idx on reservation(endTime);
CREATE INDEX resprofileID_idx on reservation(resprofileID);

GRANT ALL PRIVILEGES ON reservation.reservation TO reservation;


######################################
# Table resprofiles
######################################

CREATE TABLE IF NOT EXISTS resprofiles (
	resprofileID		INT UNSIGNED AUTO_INCREMENT,
	name				VARCHAR(255) NOT NULL,
	description         VARCHAR(1023),
	owner 				INT UNSIGNED,
	isglobaldefault		BOOLEAN,

	PRIMARY KEY (resprofileID)
);

CREATE INDEX resprofileID_idx on resprofiles(resprofileID);
CREATE INDEX name_idx on resprofiles(name);
CREATE INDEX owner_idx on resprofiles(owner);
CREATE INDEX isglobaldefault_idx on resprofiles(isglobaldefault);

GRANT ALL PRIVILEGES ON reservation.resprofiles TO reservation;


######################################
# Table ressettings
######################################

CREATE TABLE IF NOT EXISTS ressettings (
	ressettingID		INT UNSIGNED AUTO_INCREMENT,
	name				VARCHAR(255) NOT NULL,
	shortdescription	VARCHAR(255),
	description         VARCHAR(1023),
	type 				VARCHAR(255),
	ucrStart			VARCHAR(4095),
	ucrStop 			VARCHAR(4095),
	cmdStart 			VARCHAR(4095),
	cmdStop 			VARCHAR(4095),

	PRIMARY KEY (ressettingID)
);

CREATE INDEX ressettingID_idx on ressettings(ressettingID);
CREATE INDEX name_idx on ressettings(name);
CREATE INDEX type_idx on ressettings(type);

GRANT ALL PRIVILEGES ON reservation.ressettings TO reservation;


######################################
# Table resoptrel
######################################

CREATE TABLE IF NOT EXISTS resoptrel (
	resoptrelID			INT UNSIGNED AUTO_INCREMENT,
	ressettingID 		INT UNSIGNED,
	reservationID		INT UNSIGNED,
	value 				VARCHAR(4095),

	PRIMARY KEY (resoptrelID)
);

CREATE INDEX resoptrelID_idx on resoptrel(resoptrelID);
CREATE INDEX ressettingID_idx on resoptrel(ressettingID);
CREATE INDEX reservationID_idx on resoptrel(reservationID);

GRANT ALL PRIVILEGES ON reservation.resoptrel TO reservation;


######################################
# Table profoptrel
######################################

CREATE TABLE IF NOT EXISTS profoptrel (
	profoptrelID		INT UNSIGNED AUTO_INCREMENT,
	ressettingID 		INT UNSIGNED,
	resprofileID		INT UNSIGNED,
	value 				VARCHAR(4095),

	PRIMARY KEY (profoptrelID)
);

CREATE INDEX profoptrelID_idx on profoptrel(profoptrelID);
CREATE INDEX ressettingID_idx on profoptrel(ressettingID);
CREATE INDEX resprofileID_idx on profoptrel(resprofileID);

GRANT ALL PRIVILEGES ON reservation.profoptrel TO reservation;


######################################
# Table swlicenses
######################################

CREATE TABLE IF NOT EXISTS swlicenses (
	swID				INT UNSIGNED AUTO_INCREMENT,
	name				VARCHAR(255),
	description 		VARCHAR(1023),
	actScript			VARCHAR(255),
	deactScript			VARCHAR(255),
	licenses 			INT UNSIGNED,
	imageActive			BOOLEAN,

	PRIMARY KEY (swID)
);

CREATE INDEX swID_idx on swlicenses(swID);
CREATE INDEX name_idx on swlicenses(name);

GRANT ALL PRIVILEGES ON reservation.swlicenses TO reservation;


######################################
# Table vacations
######################################

CREATE TABLE IF NOT EXISTS vacations (
	vacationID			INT UNSIGNED AUTO_INCREMENT,
	name				VARCHAR(255),
	description 		VARCHAR(1023),
	startDate			DATETIME,
	endDate				DATETIME,

	PRIMARY KEY (vacationID)
);

CREATE INDEX vacationID_idx on vacations(vacationID);
CREATE INDEX name_idx on vacations(name);
CREATE INDEX startDate_idx on vacations(startDate);
CREATE INDEX endDate_idx on vacations(endDate);

GRANT ALL PRIVILEGES ON reservation.vacations TO reservation;


######################################
# Table lessontimes
######################################

CREATE TABLE IF NOT EXISTS lessontimes (
	lessonID			INT UNSIGNED AUTO_INCREMENT,
	name				VARCHAR(255),
	description 		VARCHAR(1023),
	startTime			TIME,
	endTime				TIME,

	PRIMARY KEY (lessonID)
);

CREATE INDEX lessonID_idx on lessontimes(lessonID);
CREATE INDEX name_idx on lessontimes(name);
CREATE INDEX startTime_idx on lessontimes(startTime);
CREATE INDEX endTime_idx on lessontimes(endTime);

GRANT ALL PRIVILEGES ON reservation.lessontimes TO reservation;


