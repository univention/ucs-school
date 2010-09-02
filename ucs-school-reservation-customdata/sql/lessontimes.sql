# Documentation:
# Load CSV Data
# http://dev.mysql.com/doc/refman/5.0/en/load-data.html

USE reservation;

######################################
# Table lessontimes
######################################

LOAD DATA INFILE '/usr/share/ucs-school-reservation-customdata/lessontimes.csv'
  IGNORE
  INTO TABLE lessontimes
  FIELDS TERMINATED BY ',' ENCLOSED BY '"'
  LINES TERMINATED BY '\n';

