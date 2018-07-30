Test data generation
====================

Create users
------------

To create a CSV file for the HTTP-API import of 10 students in two classes in OU ``$OU`` with email addresses run::

    $ ROLE=student
    $ OU=SchuleEins

    $ /usr/share/ucs-school-import/scripts/ucs-school-testuser-import \
        --httpapi \
        --$ROLE 10 \
        --classes 2 \
        --create-email-addresses \
        --csvfile test-http-import.csv \
        $OU

Omit the ``--csvfile`` argument to get a file with a timestamp.
To create CSV files for other roles or with different parameters run, check the help page::

    $ /usr/share/ucs-school-import/scripts/ucs-school-testuser-import --help

The contents of the file should look similar to this::

    $ cat test-http-import.csv

    "Schule","Vorname","Nachname","Klassen","Beschreibung","Telefon","EMail"
    "SchuleEins","Cia","Rothenbühler","1a","A student.","+46-728-963204","ciam.rothenbuehlerm@uni.dtr"
    "SchuleEins","Sergia","Groppel","1b","A student.","+80-043-223750","sergiam.groppelm@uni.dtr"
    [..]


A CSV file created by ``ucs-school-user-import`` with the ``--httpapi`` argument is designed to work with the configuration file ``ucs-school-testuser-http-import.json``.
 
As such, the CSV file can be imported on the command line with::

    $ /usr/share/ucs-school-import/scripts/ucs-school-user-import \
        --conffile /usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json \
        --user_role $ROLE \
        --school $OU \
        --infile test-http-import.csv \
        --sourceUID "$OU-$ROLE" \
        --verbose

The ``$OU`` in ``--sourceUID "$OU-$ROLE"`` should be lowercase, to make the import job as *similar* as possible to how it would be started by the UMC module (there will still be minor differences).

Delete users
------------

To delete the users imported with the previous command, create a CSV file with just the header line, but without user lines::

    $ head -1 test-http-import.csv > delete-all-users.csv

When running the import, make sure to specify the ``sourceUID`` correctly. The following will delete all students of ``SchuleEins`` that were imported using the HTTP-API configuration file::

    $ OU=SchuleEins
    $ ROLE=student
    $ /usr/share/ucs-school-import/scripts/ucs-school-user-import \
        --conffile /usr/share/ucs-school-import/configs/user_import_http-api.json \
        --user_role $ROLE \
        --school $OU \
        --infile delete-all-users.csv \
        --sourceUID "$OU-$ROLE" \
        --verbose
 
 
Now that you have a CSV file and a matching configuration file (in ``/var/lib/ucs-school-import/configs/user_import.json`` or/and ``/var/lib/ucs-school-import/configs/$OU.json``) that can be used with it, you can start an import using the HTTP-API.
