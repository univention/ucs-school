.. _scenarios:

*********
Szenarien
*********

In diesem Kapitel beschreiben wir Ihnen Szenarien, in denen |UCSUAS| häufig
eingesetzt wird. In diesem Dokument sind diese Szenarien in ihrem Umfang klar
voneinander abgegrenzt. In der Praxis ist diese strikte Trennung nur selten der
Fall und es treten in der Regel gemischte Formen auf. Die Umsetzung eines
bestimmten in diesem Papier beschriebenen Szenarios schließt somit nicht aus,
dass Sie im Laufe der Zeit weitere Szenarien auf Basis der bestehenden Umgebung
umsetzen können.

.. _scenario-0:

Servicestufen: |UCSUAS|
=======================

Univention bietet für die Szenarien 1 bis 4 unterschiedliche Servicestufen für
die Unterstützung in Projekten an. Kunden entscheiden beim Kauf von |UCSUAS|,
welche Servicestufe für Sie in der aktuellen Situation am passendsten ist. Ein
Wechsel auf eine andere Servicestufe ist jederzeit möglich. Voraussetzung in
allen Servicestufen ist das Vorhandensein eines User Helpdesks, der die
Supportanfragen aus den Schulen entgegen nimmt und die weitere Bearbeitung
einleitet.

Welche Servicestufen gibt es?

A. **Software und Support**: Univention liefert Software und Support, der Kunde
   kümmert sich selbst um Betrieb, Updates und Backup.

#. **Betrieb im Rechenzentrum des Kunden**: Univention liefert Software und
   Support und übernimmt Betrieb, Updates und Backup im Rechenzentrum des Kunden.

#. **UCS\@school as a Service**: Univention liefert Software und Support und
   übernimmt Betrieb, Updates und Backup im eigenen Rechenzentrum. Kunden können
   sofort starten, ohne Investitionen in Hardware oder Software tätigen zu müssen.

.. _fig-scenario-0:

.. figure:: /images/0_ucsatschool_as_a_service.png
   :alt: Servicestufen: |UCSUAS|

   Servicestufen: |UCSUAS|

.. _scenario-1:

Szenario 1: Bildungscloud
=========================

Dieses Szenario ermöglicht es Schulträgern und Ministerien, eine effiziente
Bildungscloud für ihre Schulen aufzubauen. Die Instanzen von |UCSUCS| werden
zentral in einem Rechenzentrum betrieben und stellen das Identity- und
Access-Management zur Verfügung. An dieses werden unterschiedliche IT-Angebote
angebunden, die von den Schulen benötigt werden. Zum Beispiel E-Mail und
Groupware-Lösungen oder Lernmanagement-Systeme.

Lehrkräfte und Schüler*innen können alle angeschlossenen Angebote mit einem
einzigen persönlichen Benutzerkonto und Passwort nutzen. Die Angebote können
dabei sowohl vor Ort in den Schulen als auch von unterwegs oder von zu Hause
genutzte werden.

Merkmale:

* Unabhängigkeit von der jeweiligen IT-Ausstattung der Schulen

* Bereitstellung orts- und zeitunabhängiger IT-Angebote für Lehrkräfte und
  Schüler*innen

* Effizienter Betrieb durch zentrale Administration

* Integration beliebiger IT-Angebote oder vorkonfigurierter Angebote aus dem
  Univention App Center

* Senkung des Aufkommens im Helpdesk durch Self-Service für vergessene
  Passwörter

.. _fig-scenario-1:

.. figure:: /images/1_zentrale.png
   :alt: Zentrales Identity-Management mit integrierten IT-Angeboten

   Zentrales Identity-Management mit integrierten IT-Angeboten

.. _scenario-2:

Szenario 2: Zentrales schulisches WLAN
======================================

Dieses Szenario ermöglicht es Schulträgern, den Zugang zum WLAN in ihren Schulen
zentral zu steuern und den Zugang nur bekannten Lehrkräften und Schüler*innen zu
gewähren. Dazu wird Univention Corporate Server zentral in einem Rechenzentrum
betrieben und dient als Identity- und Access-Management.

Die Schulen sind mit diesem Rechenzentrum beispielsweise mittels eines
VPN-Zugangs verbunden. In den Schulen werden WLAN Access Points installiert, die
RADIUS unterstützen (WPA2-Enterprise / IEEE 802.1X).

Ergänzend können auch wie in Szenario 1 weitere IT-Angebote an die zentralen
Systeme angebunden werden.

Merkmale:

* Unabhängigkeit von Schulserver-Lösungen in den Schulen

* Geringe zusätzliche Anforderungen an die Bandbreite der Schule

* Absicherung des WLAN-Zugangs durch Verwendung persönlicher Zugangsdaten für
  Lehrkräfte und Schüler

* Effizienter Betrieb durch zentrale Administration

* Integration beliebiger IT-Angebote oder vorkonfigurierter Angebote aus dem
  Univention App Center

.. _fig-scenario-2:

.. figure:: /images/2_zentrale_wlan.png
   :alt: Zentrales Identity-Management, WLAN und weitere IT-Angebote für Schulen

   Zentrales Identity-Management, WLAN und weitere IT-Angebote für Schulen

.. _scenario-3:

Szenario 3: Zentral verwaltete schulische IT-Infrastruktur
==========================================================

Dieses Szenario ermöglicht es Schulträgern, die gesamte IT-Infrastruktur ihrer
Schulen zentral zu verwalten und pädagogische Funktionen dezentral in den
Schulen bereitzustellen. Dazu ergänzt es die in :ref:`Szenario 2 <scenario-2>`
beschriebene WLAN Lösung um an den Schulen betriebene Schulserver. Diese stellen
vor Ort die benötigten Infrastruktur-Dienste wie DHCP, DNS, Active Directory
kompatible Domäne, Dateifreigaben, Proxy, aber auch pädagogische Funktionen wie
Computerraumsteuerung, Klassenarbeitsmodus, Passwörter zurücksetzen und
Softwareverteilung bereit.

Merkmale:

* Vollständige Bereitstellung der IT-Infrastruktur in den Schulen

* Unabhängigkeit der Schule gegenüber Ausfällen des Internetzugangs/VPNs

* Effizienter Betrieb durch zentrale Administration

* Integration beliebiger IT-Angebote oder vorkonfigurierter Angebote aus dem
  Univention App Center

.. _fig-scenario-3:

.. figure:: /images/3_zentrale_wlan_schulserver.png
   :alt: Zentral verwaltete schulische IT-Infrastruktur mit Schulservern an den Schulen

   Zentral verwaltete schulische IT-Infrastruktur mit Schulservern an den Schulen

.. _scenario-4:

Szenario 4: Schulische IT-Infrastruktur ohne dezentrale Schulserver
===================================================================

Dieses Szenario ermöglicht es Schulträgern, die gesamte IT-Infrastruktur ihrer
Schulen zentral zu verwalten, wie in :ref:`Szenario 3 <scenario-3>` beschrieben,
mit der Ergänzung, dass die Schulserver nicht in den Schulen, sondern im
Rechenzentrum betrieben werden.

Voraussetzung ist eine sehr gute und zuverlässige Anbindung der Schulen an
dieses Rechenzentrum. Durch die Verlagerung der Schulserver ins Rechenzentrum
können die Hardware-Ressourcen effizienter verwendet werden und gleichzeitig
reduzieren sich die Kosten für die Wartung.

Merkmale:

* Vollständige Bereitstellung der IT-Infrastruktur in den Schulen

* Abhängigkeit der Schule gegenüber Ausfällen des Internetzugangs/VPNs

* Effizienter Betrieb durch zentrale Administration und bessere
  Ressourcennutzung

* Effiziente Wartung durch einfacheren Zugang zu den Systemen

* Integration beliebiger IT-Angebote oder vorkonfigurierter Angebote aus dem
  Univention App Center

.. _fig-scenario-4:

.. figure:: /images/4_zentrale_wlan_schulserver_rz.png
   :alt: Zentral verwaltete schulische IT-Infrastruktur ohne dezentrale Schulserver

   Zentral verwaltete schulische IT-Infrastruktur ohne dezentrale Schulserver
