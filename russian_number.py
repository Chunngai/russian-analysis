from enum import StrEnum

from utils import list_enum_values


class RussianNumber(StrEnum):
    SG = "sg"
    PL = "pl"


RUSSIAN_NUMBERS = list_enum_values(RussianNumber)