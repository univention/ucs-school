��    ?                      e     x   s  �   �  �   �  	   h  Y   r  `   �  t   -  �   �  �   #  �   �     1	  w   �	  �   )
  b   �
  �   F  �     g   �  e     (   m  �   �     S     j     �     �     �     �  <   �  6     :   Q  :   �  :   �  :     7   =  7   u  ?   �  ?   �  ;   -  M   i  M   �  @     <   F  <   �  D   �  D     C   J  <   �  <   �  <     D   E  <   �  =   �  =     >   C  J   �  ;   �  Y   	  �   c  �   �  �     A     �   M  �  �  ~   k  �   �    �  �   �  	   _  x   i  �   �  �   i  �      �   �  �   N   �   !  �   �!  �   5"  t   #  �   �#  �   c$  l   %  p   %  )   �%  �   &  !   �&     '      9'      Z'  %   {'  %   �'  @   �'  :   (  6   C(  6   z(  6   �(  6   �(  3   )  3   S)  ;   �)  ;   �)  7   �)  I   7*  I   �*  <   �*  8   +  8   A+  @   z+  @   �+  ?   �+  8   <,  8   u,  8   �,  @   �,  8   (-  9   a-  9   �-  :   �-  F   .  7   W.  U   �.  �   �.  �   �/  �   0  O   �0  �   �0   Add the Keycloak Kerberos user SPN to the samba SPN list on replicas for new joins (:uv:bug:`57348`). Added an UCR variable to toggle the distribution to other teachers within the same class or workgroup (:uv:bug:`52712`). Added the UCR variable ``ucsschool/umc/computerroom/screenshot_dimension``, with which you can set the base screenshot size in the computer room module. A lower base screenshot size can help to improve performance (:uv:bug:`57443`). Added validation for students when they are added to an exam. This helps to detect validation errors before the exam is started (:uv:bug:`57319`). Changelog Fix SiSoPi missing :code:`ucsschoolPurgeTimestamp` for "deleted" users (:uv:bug:`50848`). Fix that the filename argument was not passed to the :code:`BaseReader` class (:uv:bug:`57600`). Fixed a bug that lead to skips in the cron controlled cleanup jobs on single server installations (:uv:bug:`53232`). Fixed a bug that would lead to a faulty configuration if there was a user with the role ``teacher_and_staff`` (:uv:bug:`57208`). Fixed a bug which would prevent teachers to reset passwords of students when they have unset extended attributes (:uv:bug:`55740`). Fixed a consistency check for non default admins group prefix. See UCRV ``ucsschool/ldap/default/groupprefix/admins``. (:uv:bug:`55884`). Fixed a performance regression which could cause significant longer startup times for the UCS\@school import (:uv:bug:`57408`). Fixed an issue that caused the user importer to not properly detect the encoding of a given CSV file (:uv:bug:`56846`). Fixed an issue that would lead to an :code:`UnknownPropertyError` when mapping extended attributes from :code:`LDAP` to :code:`UDM` and leads to crashes of the module (:uv:bug:`55740`). Fixed issues that would lead to unexpected behavior while exporting class lists (:uv:bug:`57018`). If a local user is logged into a computer that is in a computer room, the username is prefixed with ``LOCAL\`` in the computer room module instead of showing an error message (:uv:bug:`56937`). If errors occur due to incorrect samba share configuration files, they are displayed during the preparation and not during the exam (:uv:bug:`57367`). Internal Change: Reformatted source code for better readability and maintainability. (:uv:bug:`55751`). Internal change: Improve search filter for mac addresses for importing a computer. (:uv:bug:`55015`). Internal improvements (:uv:bug:`57604`). Keep the computer room responsive even if the Veyon Proxy is unstable. This will ensure that exams can be started and finished, even if Veyon functionality does not work (:uv:bug:`57604`). Released on 2024-03-21 Released on 2024-05-16 Released on 2024-07-02 Released on 2024-07-11 Released on 2024-09-13 Released on 2024-09-17 Source *ucs-school-umc-computerroom* in version ``12.0.18``: Source *ucs-school-veyon-client* in version ``2.0.6``: Source package *ucs-school-import* in version ``18.0.45``: Source package *ucs-school-import* in version ``18.0.46``: Source package *ucs-school-import* in version ``18.0.47``: Source package *ucs-school-import* in version ``18.0.50``: Source package *ucs-school-info* in version ``10.0.3``: Source package *ucs-school-lib* in version ``13.0.45``: Source package *ucs-school-metapackage* in version ``13.0.17``: Source package *ucs-school-metapackage* in version ``13.0.18``: Source package *ucs-school-netlogon* in version ``10.0.3``: Source package *ucs-school-netlogon-user-logonscripts* in version ``16.0.5``: Source package *ucs-school-netlogon-user-logonscripts* in version ``16.0.6``: Source package *ucs-school-old-sharedirs* in version ``15.0.4``: Source package *ucs-school-ox-support* in version ``4.0.4``: Source package *ucs-school-roleshares* in version ``8.0.4``: Source package *ucs-school-umc-computerroom* in version ``12.0.16``: Source package *ucs-school-umc-computerroom* in version ``12.0.17``: Source package *ucs-school-umc-distribution* in version ``18.0.9``: Source package *ucs-school-umc-exam* in version ``10.0.12``: Source package *ucs-school-umc-exam* in version ``10.0.13``: Source package *ucs-school-umc-import* in version ``3.0.8``: Source package *ucs-school-umc-internetrules* in version ``16.0.5``: Source package *ucs-school-umc-lists* in version ``3.0.10``: Source package *ucs-school-umc-rooms* in version ``17.0.10``: Source package *ucs-school-umc-users* in version ``16.0.10``: Source package *ucs-school-veyon-client* in version ``2.0.5``: Source package *ucs-school-veyon-windows* in version ``4.8.3.0-ucs5.0-0``: Source package *ucs-school-webproxy* in version ``16.0.8``: Source package *univention-management-console-module-selective-udm* in version ``9.0.4``: The ``ucs-school-purge-expired-users`` now ignores users without a UCS\@school role that is recognized by the UCS\@school Importer (:uv:bug:`55179`). The new Nubus logo replaces the UCS logo. Users who have the link for the UMC on the desktop will see the new logo (:uv:bug:`57395`). The selection in the UCS\@school UMC import was not properly localized. An updated image was placed in the documentation (:uv:bug:`56519`). Update Veyon windows client to version 4.8.3.0 (:uv:bug:`53907`). When importing a computer with an IP address starting with "255.", the user gets a warning that is logged to the console (:uv:bug:`55376`). Project-Id-Version: UCS@school - 5.0 v5 Changelog 
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2024-09-17 10:14+0000
PO-Revision-Date: 2023-08-02 09:20+0000
Last-Translator: FULL NAME <EMAIL@ADDRESS>
Language: de
Language-Team: de <LL@li.org>
Plural-Forms: nplurals=2; plural=(n != 1);
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 8bit
Generated-By: Babel 2.16.0
 Die Keycloak-Kerberos-Benutzer-SPN ist zur Samba-SPN-Liste auf Replicas für neue Joins hinzugefügt worden (:uv:bug:`57348`). Es wurde eine UCR-Variable hinzugefügt, um die Verteilung an andere Lehrer innerhalb der gleichen Klasse oder Arbeitsgruppe abzuschalten (:uv:bug:`52712`). Die UCR-Variable ``ucsschool/umc/computerroom/screenshot_dimension`` wurde hinzugefügt, mit der Sie die Basisgröße der Screenshots im Computerraum-Modul einstellen können. Eine niedrigere Basisgröße für Screenshots kann die Performance verbessern (:uv:bug:`57443`). Es wurde eine Validierung für Schüler hinzugefügt, wenn sie zu einer Prüfung hinzugefügt werden. Dies hilft, Validierungsfehler zu erkennen, bevor die Prüfung gestartet wird (:uv:bug:`57319`). Changelog Es wurde ein Fehler im SiSoPi Import behoben, bei dem der :code:`ucsschoolPurgeTimestamp` gefehlt hat (:uv:bug:`50848`). Es wurde ein Fehler behoben bei dem der Dateiname des Importes nicht der :code:`BaseReader` Klasse übergeben wurde (:uv:bug:`57547`). Es wurde ein Fehler behoben, der zum Überspringen in von Cron gesteuerten Aufräumarbeiten bei Einzelserver Installationen führte (:uv:bug:`53232`). Es wurde ein Fehler behoben, der zu einer fehlerhaften Konfiguration führte, wenn es einen Benutzer mit der Rolle ``Lehrer und Mitarbeiter`` gab (:uv:bug:`57208`). Es wurde ein Fehler behoben, der Lehrer daran hinderte, Passwörter von Schülern zurückzusetzen, wenn sie nicht gesetzte erweiterte Attribute haben (:uv:bug:`55740`). Ein Fehler in der Konsistenzprüfung für nicht standardmäßige Gruppenpräfixe von Schuladministratoren wurde behoben. Siehe UCRV ``ucsschool/ldap/default/groupprefix/admins``. (:uv:bug:`55884`). Es wurde eine Performance Regression behoben, die zu deutlich längeren Startzeiten für den UCS\@school Import führen konnte (:uv:bug:`57408`). Ein Problem wurde behoben, das dazu führte, dass der Benutzer Importer die Kodierung einer CSV-Datei nicht richtig erkennt. (:uv:bug:`56846`) Es wurde ein Problem behoben, das zu einem :code:`UnknownPropertyError` führte, wenn erweiterte Attribute von :code:`LDAP` auf :code:`UDM` abgebildet wurden und zu Abstürzen des Moduls führte (:uv:bug:`55740`). Probleme behoben, die zu unerwartetem Verhalten beim Exportieren von Klassenlisten führen konnten (:uv:bug:`57018`) Wenn ein lokaler Benutzer an einem Computer angemeldet ist, der sich in einem Computerraum befindet, wird dem Benutzernamen im Computerraummodul ``LOCAL\`` vorangestellt, anstatt eine Fehlermeldung anzuzeigen (:uv:bug:`56937`) Wenn Fehler aufgrund falscher Samba-Freigabekonfigurationsdateien auftreten, werden sie während der Vorbereitung und nicht während der Prüfung angezeigt (:uv:bug:`57367`). Interne Änderung: Umformatierung des Quellcodes zur besseren Lesbarkeit und Wartbarkeit. (:uv:bug:`55751`). Interne Änderung: Verbesserter Suchfilter für Mac-Adressen beim Importieren eines Computers (:uv:bug:`55015`). Interne Verbesserungen (:uv:bug:`57604`). Das Computerraum Modul bleibt nun weiterhin nutzbar, selbst wenn der Veyon Proxy instabil ist.Das erlaubt es zum Beispiel Klassenarbeiten zu starten und zu beenden, selbst wenn Veyon nicht funktioniert (:uv:bug:`57604`). Veröffentlicht am 21. März 2024 Veröffentlicht am 16. Mai 2024 Veröffentlicht am 02. Juli 2024 Veröffentlicht am 11. Juli 2024 Veröffentlicht am 13. September 2024 Veröffentlicht am 17. September 2024 Quellpaket *ucs-school-umc-computerroom* in Version ``12.0.18``: Quellpaket *ucs-school-veyon-client* in Version ``2.0.6``: Quellpaket *ucs-school-import* in Version ``18.0.45``: Quellpaket *ucs-school-import* in Version ``18.0.46``: Quellpaket *ucs-school-import* in Version ``18.0.47``: Quellpaket *ucs-school-import* in Version ``18.0.50``: Quellpaket *ucs-school-info* in Version ``10.0.3``: Quellpaket *ucs-school-lib* in Version ``13.0.45``: Quellpaket *ucs-school-metapackage* in Version ``13.0.17``: Quellpaket *ucs-school-metapackage* in Version ``13.0.18``: Quellpaket *ucs-school-netlogon* in Version ``10.0.3``: Quellpaket *ucs-school-netlogon-user-logonscripts* in Version ``16.0.5``: Quellpaket *ucs-school-netlogon-user-logonscripts* in Version ``16.0.6``: Quellpaket *ucs-school-old-sharedirs* in Version ``15.0.4``: Quellpaket *ucs-school-ox-support* in Version ``4.0.4``: Quellpaket *ucs-school-roleshares* in Version ``8.0.4``: Quellpaket *ucs-school-umc-computerroom* in Version ``12.0.16``: Quellpaket *ucs-school-umc-computerroom* in Version ``12.0.17``: Quellpaket *ucs-school-umc-distribution* in Version ``18.0.9``: Quellpaket *ucs-school-umc-exam* in Version ``10.0.12``: Quellpaket *ucs-school-umc-exam* in Version ``10.0.13``: Quellpaket *ucs-school-umc-import* in Version ``3.0.8``: Quellpaket *ucs-school-umc-internetrules* in Version ``16.0.5``: Quellpaket *ucs-school-umc-lists* in Version ``3.0.10``: Quellpaket *ucs-school-umc-rooms* in Version ``17.0.10``: Quellpaket *ucs-school-umc-rooms* in Version ``17.0.10``: Quellpaket *ucs-school-veyon-client* in Version ``2.0.5``: Quellpaket *ucs-school-veyon-windows* in Version ``4.8.3.0-ucs5.0-0``: Quellpaket *ucs-school-webproxy* in Version ``16.0.8``: Quellpaket *univention-management-console-module-selective-udm* in Version ``9.0.4``: Das Programm ``ucs-school-purge-expired-users`` ignoriert nun Benutzer mit UCS\@school Rollen, die nicht vom UCS\@school Importer erkannt werden (:uv:bug:`55179`). Das neue Nubus-Logo ersetzt das UCS-Logo. Benutzer, die den Link für die UMC auf dem Desktop haben, werden das neue Logo sehen (:uv:bug:`57395`). Die Auswahl im UCS\@school UMC-Import ist nun korrekt lokalisiert. Ein aktualisiertes Bild ist in der Dokumentation enthalten (:uv:bug:`56519`). Aktualisierung des Veyon Windows Clients auf Version 4.8.3.0 (:uv:bug:`53907`). Beim Importieren eines Computers mit einer IP-Adresse, die mit "255." beginnt, erhält der Benutzer eine Warnung, die auf der Konsole protokolliert wird (:uv:bug:`55376`). 