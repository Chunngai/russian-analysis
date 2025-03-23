from enum import StrEnum

from russian_gender import RussianGender, RUSSIAN_GENDERS
from russian_case import RussianCase, RUSSIAN_CASES
from russian_number import RussianNumber
from russian_word import RussianWord

from utils import get_accent_pos, get_pos_of_last_vowel, remove_accent_mark, insert_accent_mark, list_enum_values, has_single_vowel, RUSSIAN_REFLEXIVE_SUFFIX_CJA


RUSSIAN_ADJECTIVE_DECLENSION_SHORT = "short"
RUSSIAN_ADJECTIVE_DECLENSION_COMPARATIVE = "comparative"
RUSSIAN_ADJECTIVE_DECLENSION_SUPERLATIVE = "superlative"


RussianAdjectiveDeclensionType = StrEnum(
    "RussianAdjectiveDeclensionType",
    {
        d.upper(): d
        for d in [
            f"{case_or_short}_{gender_or_pl}"
            for case_or_short in RUSSIAN_CASES + [RUSSIAN_ADJECTIVE_DECLENSION_SHORT]
            for gender_or_pl in RUSSIAN_GENDERS + [RussianNumber.PL]
        ] + [RUSSIAN_ADJECTIVE_DECLENSION_COMPARATIVE, RUSSIAN_ADJECTIVE_DECLENSION_SUPERLATIVE]
    }
)


RUSSIAN_ADJECTIVE_DECLENSION_TYPES = list_enum_values(RussianAdjectiveDeclensionType)


RUSSIAN_ADJECTIVE_DECLENSION_HARD_SUFFICES = {
    RussianCase.NOM: {
        RussianGender.M: "ый",
        RussianGender.F: "ая",
        RussianGender.N: "ое",
        RussianNumber.PL: "ые",
    },
    RussianCase.GEN: {
        RussianGender.M: "ого",
        RussianGender.F: "ой",
        RussianGender.N: "ого",
        RussianNumber.PL: "ых",
    },
    RussianCase.DAT: {
        RussianGender.M: "ому",
        RussianGender.F: "ой",
        RussianGender.N: "ому",
        RussianNumber.PL: "ым",
    },
    RussianCase.ACC: {
        RussianGender.M: ("ый", "ого"),
        RussianGender.F: "ую",
        RussianGender.N: "ое",
        RussianNumber.PL: ("ые", "ых"),
    },
    RussianCase.INST: {
        RussianGender.M: "ым",
        RussianGender.F: ("ой", "ою"),
        RussianGender.N: "ым",
        RussianNumber.PL: "ыми",
    },
    RussianCase.PREP: {
        RussianGender.M: "ом",
        RussianGender.F: "ой",
        RussianGender.N: "ом",
        RussianNumber.PL: "ых",
    },
    RUSSIAN_ADJECTIVE_DECLENSION_SHORT: {
        RussianGender.M: "",
        RussianGender.F: "а",
        RussianGender.N: "о",
        RussianNumber.PL: "ы",
    },
}


RUSSIAN_ADJECTIVE_DECLENSION_HARD2SOFT = {
    "ы": "и",
    "а": "я",
    "о": "е",
    "у": "ю",
}


def hard2soft(suffices):
    if type(suffices) == str:
        return RUSSIAN_ADJECTIVE_DECLENSION_HARD2SOFT.get(
            suffices[0],
            suffices[0],
        ) + suffices[1:]
    else:
        soft_suffices = []
        for i in range(len(suffices)):
            soft_suffices.append(RUSSIAN_ADJECTIVE_DECLENSION_HARD2SOFT.get(
                suffices[i][0],
                suffices[i][0],
            ) + suffices[i][1:])
        return tuple(soft_suffices)



RUSSIAN_ADJECTIVE_DECLENSION_SOFT_SUFFICES = {
    case_or_short: {
        gender_or_pl: (
            hard2soft(suffices)
            if suffices
            else ""
        )
        for gender_or_pl, suffices in RUSSIAN_ADJECTIVE_DECLENSION_HARD_SUFFICES[case_or_short].items()
    }
    for case_or_short in RUSSIAN_ADJECTIVE_DECLENSION_HARD_SUFFICES
}


class RussianAdjective(RussianWord):

    special_suffix_mapping = {
        "г": "ж",
        "к": "ч",
        "х": "ш",
        "д": "ж",
        "т": "ч",
        "ст": "щ",
    }

    def __init__(self, accented: str):
        
        super().__init__(accented=accented)

        self.is_soft = (
            self.bare.endswith("ий")
            and self.bare[-3] not in "гкхшжщчц"
        )
        self.suffix_mapping = (
            RUSSIAN_ADJECTIVE_DECLENSION_HARD_SUFFICES
            if not self.is_soft
            else RUSSIAN_ADJECTIVE_DECLENSION_SOFT_SUFFICES
        )

        self.ends_with_oi = self.bare.endswith("ой")

        self.has_reflexive_suffix = self.bare.endswith(RUSSIAN_REFLEXIVE_SUFFIX_CJA)

        self.stem = self.bare[:-2]
        if self.has_reflexive_suffix:
            self.stem = self.stem[:-2]

        self.special_suffix = None
        for special_suffix in self.special_suffix_mapping:
            if self.stem.endswith(special_suffix):
                self.special_suffix = special_suffix
                # Do not break.
                # E.g., firstly matched "т",
                # but actually should match "ст".
                # If with break, "ст" will not be matched.
                # break

    def get_suffices(self, case_or_short, gender_or_pl):
        suffices = self.suffix_mapping.get(
            case_or_short,
            {}
        ).get(
            gender_or_pl,
        )
        return suffices
    
    def __getattribute__(self, name):
        
        if name not in RUSSIAN_ADJECTIVE_DECLENSION_TYPES:
            return super().__getattribute__(name)

        decl_form = ""

        if name == RUSSIAN_ADJECTIVE_DECLENSION_COMPARATIVE:
            decl_form = self._comparative
        elif name == RUSSIAN_ADJECTIVE_DECLENSION_SUPERLATIVE:
            decl_form = self._superlative
        else:
            case_or_short, gender_or_pl = name.split("_")
            if case_or_short != RUSSIAN_ADJECTIVE_DECLENSION_SHORT:
                case_or_short = RussianCase(case_or_short)
            if gender_or_pl in RUSSIAN_GENDERS:
                gender_or_pl = RussianGender(gender_or_pl)
            else:
                gender_or_pl = RussianNumber(gender_or_pl)

            suffices = self.get_suffices(
                case_or_short=case_or_short,
                gender_or_pl=gender_or_pl,
            )
            if type(suffices) == str:
                suffices = [suffices]
            suffices = list(suffices)

            if (
                case_or_short in [RussianCase.NOM, RussianCase.ACC]
                and gender_or_pl == RussianGender.M
                and self.ends_with_oi
            ):
                for i in range(len(suffices)):
                    if suffices[i] == "ый":
                        suffices[i] = "ой"

            forms = []
            for suffix in suffices:
                forms.append(self.apply_declension(
                    stem=self.stem,
                    suffix=suffix,
                ))
                if self.has_reflexive_suffix:
                    forms[-1] += RUSSIAN_REFLEXIVE_SUFFIX_CJA
            decl_form = "/".join(forms)
        
        return decl_form        

    @property
    def _comparative(self):
        
        if self.special_suffix is not None:

            mapped_suffix = self.special_suffix_mapping[self.special_suffix]
            cmp_stem = self.stem[:-len(self.special_suffix)] + mapped_suffix

            cmp_accent_pos = self.accent_pos
            if cmp_accent_pos >= len(cmp_stem):
                cmp_accent_pos = get_pos_of_last_vowel(cmp_stem)

            cmp = cmp_stem + "е"

        else:

            cmp = self.stem + "ее"

            if has_single_vowel(self.stem):
                cmp_accent_pos = len(cmp) - 2  # е'е
            else:
                cmp_accent_pos = self.accent_pos

        cmp = insert_accent_mark(
            word=cmp,
            accent_pos=cmp_accent_pos,
        )
        return cmp


    @property
    def _superlative(self):
        
        if self.special_suffix == "ст":
            self.special_suffix = None
        if self.special_suffix is not None:

            mapped_suffix = self.special_suffix_mapping[self.special_suffix]
            sup_stem = self.stem[:-len(self.special_suffix)] + mapped_suffix

            sup = sup_stem + "айший"

            sup_accent_pos = len(sup) - 5

        else:

            sup = self.stem + "ейший"

            if has_single_vowel(self.stem):
                sup_accent_pos = len(sup) - 5  # е'йший
            else:
                sup_accent_pos = self.accent_pos

        sup = insert_accent_mark(
            word=sup,
            accent_pos=sup_accent_pos
        )
        return sup
