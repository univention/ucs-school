import datetime
from enum import StrEnum
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple, TypedDict, Union

from pydantic import BaseModel, ConstrainedStr, EmailStr, Extra, Field as PydanticField


class SchoolUserRole(StrEnum):
    student = "student"
    teacher = "teacher"
    school_admin = "school_admin"
    staff = "staff"


class RankineBaseModel(BaseModel):
    class Config:
        allow_population_by_field_name = True


class ListViewGlobalAction(StrEnum):
    CREATE = "create"


class AddViewAction(StrEnum):
    SAVE = "save"


class ListViewObjectAction(StrEnum):
    DELETE = "delete"
    DETAIL = "detail"


class DetailViewAction(StrEnum):
    EDIT = "edit"


class FieldType(StrEnum):
    CHECKBOX = "UInputCheckbox"
    COMBOBOX = "UComboBox"
    DATEBOX = "UInputDate"
    MULTIINPUT = "UMultiInput"
    MULTIOBJECTSELECT = "UMultiObjectSelect"
    MULTISELECT = "UMultiSelect"
    PASSWORDBOX = "UInputPassword"
    SELECT = "USelect"
    TEXTBOX = "UInputText"


class Field(RankineBaseModel):
    type: FieldType
    props: Dict[str, Any]


class Fieldset(RankineBaseModel):
    label: str
    name: str
    rows: List[List[Field]]


class Page(RankineBaseModel):
    label: str
    name: str
    fieldsets: List[Fieldset]


NonEmptyStr = PydanticField(min_length=1)


class Access(StrEnum):
    NONE = "none"
    READ = "read"
    WRITE = "write"


class Attribute(BaseModel):
    value: Any
    access: Access


class BooleanAttribute(Attribute):
    value: Optional[bool]
    access: Access


class DateAttribute(Attribute):
    value: Optional[datetime.date]
    access: Access


class DatetimeAttribute(Attribute):
    value: Optional[datetime.datetime]
    access: Access


class ListOfStringsAttribute(Attribute):
    value: Optional[List[str]]
    access: Access


class StringAttribute(Attribute):
    value: Optional[str]
    access: Access


class EmptyString(ConstrainedStr):
    max_length = 0


class SchoolGroupType(StrEnum):
    SCHOOL_CLASS = "school_class"
    WORKGROUP = "workgroup"


class SchoolGroup(BaseModel):
    name: str
    type: SchoolGroupType


class SchoolData(BaseModel):
    name: str
    primary: bool
    roles: List[str]
    school_groups: List[SchoolGroup]


class CreateUserModel(RankineBaseModel, extra=Extra.allow):
    username: str = NonEmptyStr
    firstname: str = NonEmptyStr
    lastname: str = NonEmptyStr
    password: Optional[str]
    birthday: Optional[Union[datetime.date, EmptyString]]
    disabled: Optional[bool]
    email: Optional[EmailStr] = None
    school_data: Dict[str, SchoolData]
    create_timestamp: DatetimeAttribute
    modify_timestamp: DatetimeAttribute
    expiration_date: DateAttribute
    ucsschool_purge_timestamp: DateAttribute
    source_uid: Optional[str]
    record_uid: Optional[str]


class CreateUserResponseModel(BaseModel):
    school_data: List[str]
    username: str
    email: Optional[EmailStr] = None


ListedUserAttributes = Dict[str, Any]


class UserListResponseModel(RankineBaseModel):
    id: str
    allowed_actions: List[ListViewObjectAction]
    attributes: ListedUserAttributes


class UserDetailResponseModel(RankineBaseModel):
    url: str
    allowed_actions: List[DetailViewAction]
    pages: List[Page]
    values: Dict[str, Any]


class GroupKind(StrEnum):
    SCHOOL_CLASS = "school_class"
    WORKGROUP = "workgroup"


PatchUser = Dict[str, Any]


class DetailException(BaseModel):
    detail: str


class ValidationError(TypedDict):
    loc: Tuple[Union[int, str], ...]
    msg: str
    type: str


class ValidationException(BaseModel):
    detail: List[ValidationError]


class PageAddViewResponseModel(RankineBaseModel):
    url: str
    allowed_actions: List[AddViewAction]
    pages: List[Page]


class Sorting(StrEnum):
    ASC = "asc"
    DEC = "dec"
    NONE = "none"


class ExcludeNoneBaseModel(BaseModel):
    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        kwargs.pop("exclude_none", None)
        return super().dict(*args, exclude_none=True, **kwargs)


class ListFormatter(ExcludeNoneBaseModel):
    type: Literal["list"]


class BooleanFormatter(ExcludeNoneBaseModel):
    type: Literal["boolean"]
    truthyLabel: Optional[str]
    falsyLabel: Optional[str]


class DateFormatter(ExcludeNoneBaseModel):
    type: Literal["date"]
    withTime: Optional[bool]
    locale: Optional[str]
    dateTimeFormatOptions: Optional[Dict[str, Any]]


Formatter = Annotated[
    Union[ListFormatter, BooleanFormatter, DateFormatter], PydanticField(discriminator="type")
]


class Column(ExcludeNoneBaseModel):
    label: str
    attribute: str
    sorting: Sorting
    formatter: Optional[Formatter]
    sort_formatter: Optional[Formatter]


class PageListViewResponseModel(RankineBaseModel):
    url: str
    allowed_global_actions: List[ListViewGlobalAction]
    search_form_options: List[Field]
    columns: List[Column]


PageAddViewResponseModel.update_forward_refs()
PageListViewResponseModel.update_forward_refs()


class MultiUserResponse(RankineBaseModel):
    all_ok: bool
    successful_users: List[str]
    errors: Dict[str, str]  # mapping from username to error message
