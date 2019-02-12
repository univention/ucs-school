#!/usr/bin/python
# -*- coding: utf-8 -*-
# This script will check if all of the screenshots for the manuals and website
# exist. It will take into account different languages.

import argparse
import copy
import os

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument(
	'-v', '--verbose', dest='verbose', action='store_true',
	help='Show descriptions for the missing images.'
)
args = parser.parse_args()

search_path = './'


class Lang(object):
	DE = 'de'
	EN = 'en'
	FR = 'fr'


class Screenshot(object):
	def __init__(self, base_name, req_langs, desc=""):
		self.base_name = base_name
		self.req_langs = req_langs
		self.desc = desc


needed_screenshots = [
	#Screenshot(".. todo", [Lang.DE, Lang.FR], desc="Bildschirmpräsentation starten"),
	#Screenshot(".. todo", [Lang.DE, Lang.FR], desc="Klassenarbeit starten"),
	#Screenshot(".. todo", [Lang.DE, Lang.FR], desc="Klassenarbeit PCs neu starten"),
	#Screenshot(".. todo", [Lang.DE, Lang.FR], desc="Computerraum im Klassenarbeitsmodus"),
	Screenshot("appcenter_search_school", [Lang.DE], desc="App Center Suche"),
	Screenshot("appcenter_ucsschool", [Lang.DE], desc="App Center"),
	Screenshot("assign_classes_to_teacher", [Lang.DE, Lang.FR], desc="Lehrern Klassen zuweisen"),
	Screenshot("assign_teachers_to_class", [Lang.DE, Lang.FR], desc="Klassen Lehrer zuweisen"),
	Screenshot("computerroom_1_select", [Lang.DE, Lang.FR], desc="Computerraum auswählen"),
	Screenshot("computerroom_2_overview", [Lang.DE, Lang.FR, Lang.EN], desc="Computerraum Übersicht"),
	Screenshot("computerroom_3_start_presentation", [Lang.DE, Lang.FR], desc="Start des Präsentationsmodus bestätigen"),
	Screenshot("computerrooms_1_overview", [Lang.DE, Lang.FR], desc="Computerraum verwalten"),
	Screenshot("computerrooms_2_add_computers", [Lang.DE, Lang.FR], desc="Computerraum Computer hinzufügen"),
	Screenshot("distribution_projects_1", [Lang.DE, Lang.FR], desc="Projekübersicht"),
	Screenshot("distribution_projects_2", [Lang.DE, Lang.FR, Lang.EN], desc="Projektdetails ansehen"),
	Screenshot("distribution_projects_3", [], desc="Projekt austeilen"),
	Screenshot("distribution_projects_4", [Lang.DE, Lang.FR], desc="Projekt einsammlen bestätigen"),
	Screenshot("exam_0_start", [Lang.DE, Lang.EN], desc="Klassenarbeit starten"),
	Screenshot("exam_1_reboot", [Lang.DE, Lang.FR], desc="Neustart der Rechner für Klassenarbeitsmodus bestätigen"),
	Screenshot("exam_2_computerroom", [Lang.DE, Lang.FR], desc="Computerraum während einer Klassenarbeit"),
	Screenshot("firefox_ssl_certificate", [Lang.DE, Lang.FR], desc="Zertifikatswarnung im Firefox"),
	Screenshot("helpdesk", [Lang.DE, Lang.FR], desc="Helpdesk mit Monitorproblem kontaktieren"),
	Screenshot("internet_rules_1", [Lang.DE, Lang.FR], desc="Internetregeln übersicht"),
	Screenshot("internet_rules_2", [Lang.DE, Lang.FR], desc="Internetregeln festlegen"),
	Screenshot("lesson_times", [Lang.DE, Lang.FR], desc="Unterrichtzeiten definieren"),
	Screenshot("login", [Lang.DE, Lang.FR], desc="Anmeldung an der UMC"),
	Screenshot("module_overview_admin_admin", [], desc=""),
	Screenshot("module_overview_Administrator_admin", [Lang.DE, Lang.FR, Lang.EN], desc="Modulübersicht Verwaltung als Administrator"),
	Screenshot("module_overview_teacher_admin", [Lang.DE, Lang.EN], desc=""),
	Screenshot("module_overview_teacher_education", [Lang.DE, Lang.EN], desc=""),
	Screenshot("passwords_students_1", [Lang.DE, Lang.FR, Lang.EN], desc="Passwörter zurücksetzen Übersicht"),
	Screenshot("passwords_students_2", [Lang.DE, Lang.FR, Lang.EN], desc="Passwörter zurücksetzen Übersicht, Auswahl Klasse"),
	Screenshot("passwords_students_3", [Lang.DE, Lang.FR, Lang.EN], desc="Dialogfenster zum Passwortreset"),
	Screenshot("passwords_students_4", [Lang.DE, Lang.EN], desc="Passwörter zurücksetzen, Hintergrund Liste der Schüler, Vordergrund Reset-Dialog"),
	Screenshot("portal_ucsschool", [Lang.DE, Lang.EN], desc="UCS Portalseite mit UCS@school und Icons für Mail, Dateitausch, Lernplattform"),
	Screenshot("printer_moderation_1", [Lang.DE, Lang.FR], desc="Übersicht Druckjobs"),
	Screenshot("printer_moderation_2", [Lang.DE, Lang.FR], desc="Drucker für Druckjob auswählen"),
	Screenshot("school-italc-lock", [Lang.DE], desc="Lockscreen von iTALC"),
	Screenshot("wizard_add_user", [Lang.DE, Lang.EN], desc="Benutzer hinzufügen"),
	Screenshot("workgroup_1_selected", [Lang.DE, Lang.FR, Lang.EN], desc="Arbeitsgruppe aus Liste auswählen"),
	Screenshot("workgroup_2_add_students", [Lang.DE, Lang.FR], desc="Schüler einer Arbeitsgruppe hinzufügen")
]


def screenshot_path(screenshot, language):
	if language == Lang.DE:
		img_name = "%s.png" % (screenshot.base_name)
	else:
		img_name = "%s_%s.png" % (screenshot.base_name, language)
	return search_path + img_name


def screenshot_count(screenshots):
	count = 0
	for screenshot in screenshots:
		for language in screenshot.req_langs:
			count += 1
	return count


missing_screenshots = []
for screenshot in needed_screenshots:
	missing_screenshot = copy.deepcopy(screenshot)
	missing_screenshot.req_langs = []
	for lang in screenshot.req_langs:
		path = screenshot_path(screenshot, lang)
		if not os.path.isfile(path):
			missing_screenshot.req_langs.append(lang)
	if missing_screenshot.req_langs:
		missing_screenshots.append(missing_screenshot)

if missing_screenshots:
	print(
		"These %d of the %d required screenshots are missing:"
		% (screenshot_count(missing_screenshots), screenshot_count(needed_screenshots))
	)
else:
	print("All required screenshots exist.")
for screenshot in missing_screenshots:
	for lang in screenshot.req_langs:
		path = screenshot_path(screenshot, lang)
		print(path)
		if args.verbose:
			print("\t↳ Description: %s" % (screenshot.desc,))
