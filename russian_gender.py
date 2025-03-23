from enum import StrEnum

from utils import list_enum_values


class RussianGender(StrEnum):
    M = "m"
    F = "f"
    N = "n"


RUSSIAN_GENDERS = list_enum_values(RussianGender)