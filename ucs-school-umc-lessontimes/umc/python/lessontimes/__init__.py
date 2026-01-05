#!/usr/bin/python3
#
# Univention Management Console
#  Configure the lessons times
#
# SPDX-FileCopyrightText: 2012-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from ucsschool.lib.school_umc_base import SchoolBaseModule
from ucsschool.lib.schoollessons import SchoolLessons
from univention.lib.i18n import Translation
from univention.management.console.log import MODULE

_ = Translation("ucs-school-umc-lessontimes").translate


class Instance(SchoolBaseModule):
    def init(self):
        SchoolBaseModule.init(self)
        self._lessons = SchoolLessons()

    def get(self, request):
        lessons = self._lessons.lessons

        result = []
        for lesson in lessons:
            result.append([lesson.name, str(lesson.begin), str(lesson.end)])

        self.finished(request.id, result)

    def set(self, request):
        # remove all lessons
        for lesson in self._lessons.lessons:
            self._lessons.remove(lesson)

        try:
            # add the new lessons
            for lesson in request.options.get("lessons", []):
                (description, begin, end) = lesson
                if begin == end == "00:00" and not description:
                    continue
                elif not description:
                    raise ValueError(_("A description for a lesson is missing"))
                else:
                    self._lessons.add(description, begin, end)
            self._lessons.save()
        except (ValueError, AttributeError) as err:
            MODULE.info(str(err))
            result = {"message": str(err)}
            self.finished(request.id, result)
        else:
            self.finished(request.id, None, _("Lesson times were successfully set"))
