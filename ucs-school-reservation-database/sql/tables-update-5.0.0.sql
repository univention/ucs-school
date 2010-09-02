# Documentation:
# Create Table syntax:
# http://dev.mysql.com/doc/refman/5.1/de/create-table.html
# Datatypes
# http://dev.mysql.com/doc/refman/5.1/de/numeric-types.html

USE reservation;

######################################
# Table reservation
######################################

# add additional column
ALTER TABLE reservation ADD COLUMN deleteFlag BOOLEAN;
