from enum import StrEnum

from utils import list_enum_values


class RussianCase(StrEnum):
    NOM = "nom"
    GEN = "gen"
    DAT = "dat"
    ACC = "acc"
    INST = "inst"
    PREP = "prep"


RUSSIAN_CASES = list_enum_values(RussianCase)