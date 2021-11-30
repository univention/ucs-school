# Build instructions for the Manual in UCS@school 4.4

In UCS@school 4.4 the documentation currently has to be build locally. 
This is due to the fact, that the links in the bibliography are inserted in `doc-common` pointing to UCS 5.0.
So far, we don't have a mechanism which support links to different UCS versions.
 
1. `git clone git@git.knut.univention.de:univention/doc-common.git`
2. change the UCS version, e.g. with `sed -i 's/5\.0\./4.4./g' stylesheets/bibliography-*.xml`
3. run the spellcheck `cd ~/git/ucsschool/doc/manual/ ; make spell COMMON_DIR=../../../doc-common`
4. build the documentation with `cd ~/git/ucsschool/doc/manual/ ; make COMMON_DIR=../../../doc-common`
5. don't commit anything with the `4.4` version but roll back the changes.
6. Only copy the HTML & PDF files to the repo `docs.univention.de`
7. Check that the links in the bibliography point to the UCS 4.4 pages and not UCS 5.0.


