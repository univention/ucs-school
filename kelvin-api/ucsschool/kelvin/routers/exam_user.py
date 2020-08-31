# Copyright 2020 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import logging

from fastapi import APIRouter, Depends, Query, Security, status
from starlette.requests import Request

from ucsschool.importer.models.import_user import ImportUser
from udm_rest_client import UDM

from ..constants import OAUTH2_SCOPES
from ..token_auth import get_current_active_user
from .base import APIAttributesMixin, UcsSchoolBaseModel, udm_ctx

logger = logging.getLogger(__name__)
router = APIRouter()


class UserBaseModel(UcsSchoolBaseModel):
    class Config(UcsSchoolBaseModel.Config):
        lib_class = ImportUser


class UserCreateModel(UserBaseModel):
    class Config(UserBaseModel.Config):
        ...


class ExamUserModel(UserBaseModel, APIAttributesMixin):
    class Config(UserBaseModel.Config):
        ...

    async def from_lib_student(
        student_name: str, exam: str, room: str, request: Request, udm: UDM
    ):
        return ExamUserModel()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ExamUserModel,
    dependencies=[
        Security(
            get_current_active_user, scopes=[str(OAUTH2_SCOPES["exam_user"]["create"])]
        )
    ],
)
async def create(
    request: Request, username: str, exam: str, room: str, udm: UDM = Depends(udm_ctx),
) -> ExamUserModel:
    return await ExamUserModel.from_lib_student(username, exam, room, request, udm)


@router.delete(
    "/{username}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Security(
            get_current_active_user, scopes=[str(OAUTH2_SCOPES["exam_user"]["delete"])]
        )
    ],
)
async def delete(
    request: Request,
    username: str,
    exam: str = Query(
        None,
        description="Name of the exam the user should be removed from (required).",
    ),
    school: str = Query(
        None, description="School (OU) where the exam is being written."
    ),
    udm: UDM = Depends(udm_ctx),
) -> None:
    ...
    # TODO: this will created URLs like this:
    # /exam_user/<username>?exam=<EXAM-NAME>&school=<OU>
    # where both parameters exam and school are required. Being required, it should be like this:
    # /exam_user/<OU>/<EXAM-NAME>/<username>
