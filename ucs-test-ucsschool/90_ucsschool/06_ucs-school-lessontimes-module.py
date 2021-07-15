#!/usr/share/ucs-test/runner pytest-3 -s -l -v
# -*- coding: utf-8 -*-
## desc: ucs-school-lessontimes-module
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: careful
## packages: [ucs-school-umc-lessontimes]

from univention.testing.umc import Client


def getLessons(connection):
    return connection.umc_command("lessontimes/get").result


def addLesson(connection, name, begin, end):
    lesson = [name, begin, end]
    lessonsList = getLessons(connection)
    lessonsList.append(lesson)
    return connection.umc_command("lessontimes/set", {"lessons": lessonsList}).result


def delLesson(connection, name, begin, end):
    lessonsList = getLessons(connection)
    for item in lessonsList:
        if name in item:
            lessonsList.remove(item)
    param = {"lessons": lessonsList}
    return connection.umc_command("lessontimes/set", param).result


def test_ucs_school_lessontimes_module():
    connection = Client.get_test_connection(language="en-US")
    connection.umc_set({"locale": "en_US"})

    # 1 adding a lesson
    addLesson(connection, "99. Stunde", "00:00", "0:05")

    # 2 checking time format
    obj = addLesson(connection, "98. Stunde", "40", "80")["message"]
    assert "invalid time format" in obj, "invalid time format is not detected: %s" % obj

    # 3 check overlapping in time
    eng = "Overlapping lessons are not allowed"
    obj = addLesson(connection, "98. Stunde", "00:03", "0:06")["message"]
    assert eng in obj, "Overlapping lessons time is not detected: %s" % obj

    # 4 check overlapping in names
    obj = addLesson(connection, "99. Stunde", "00:06", "0:08")["message"]
    assert eng in obj, "Overlapping lessons names is not detected: %s" % obj

    # 5 removing a lesson
    delLesson(connection, "99. Stunde", "00:00", "1:00")
