CREATE DATABASE IF NOT EXISTS reservation DEFAULT CHARACTER SET 'utf8' COLLATE 'utf8_general_ci';

# this does not work, see http://bugs.mysql.com/bug.php?id=36776
# CREATE USER IF NOT EXISTS reservation;
CREATE USER reservation;

# For "load data infile" the priviledge "FILE" has to be grantet. This only works on a global level.
# http://dev.mysql.com/doc/refman/5.0/en/grant.html
GRANT FILE ON *.* TO reservation;
