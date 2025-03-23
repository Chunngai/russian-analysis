from enum import StrEnum

from russian_gender import RussianGender
from russian_case import RUSSIAN_CASES
from russian_number import RUSSIAN_NUMBERS
from russian_word import RussianWord
from utils import get_accent_pos, remove_accent_mark, insert_accent_mark, list_enum_values


class RussianNounSuffix(StrEnum):

    M_C = "#"  # Consonants.
    M_JI = "й"
    M_S = "ь"  # Soft sign.

    F_A = "а"
    F_JA = "я"
    F_S = "ь"  # Soft sign.

    N_O = "о"
    N_JE = "е"


RussianNounDeclensionType = StrEnum(
    "RussianNounDeclensionType",
    {
        f"{case}_{number}".upper(): f"{case}_{number}" 
        for case in RUSSIAN_CASES
        for number in RUSSIAN_NUMBERS
    }
)


RUSSIAN_NOUN_DECLENSION_TYPES = list_enum_values(RussianNounDeclensionType)


class RussianNoun(RussianWord):

    def __init__(self, accented: str, gender: str, is_animate: bool):

        super().__init__(accented=accented)

        self.gender = gender
        self.is_animate = is_animate

        self._bare = self.bare
        if (
            self.gender == RussianGender.M 
            and self.bare[-1] not in "йь"
        ):
            self._bare += "#"

        self.stem = self._bare[:-1]

    def get_suffix(self, declension_rules):
        suffix = declension_rules.get(self.gender, {}).get(self._bare[-1])
        return suffix

    @property
    def nom_sg(self):
        return insert_accent_mark(
            self.bare,
            self.accent_pos,
        )

    @property
    def nom_pl(self):
        suffix = self.get_suffix({
            RussianGender.M: {
                RussianNounSuffix.M_C: "ы",
                RussianNounSuffix.M_JI: "и",
                RussianNounSuffix.M_S: "и",
            },
            RussianGender.F: {
                RussianNounSuffix.F_A: "ы",
                RussianNounSuffix.F_JA: "и",
                RussianNounSuffix.F_S: "и",
            },
            RussianGender.N: {
                RussianNounSuffix.N_O: "а",
                RussianNounSuffix.N_JE: "я",
            },
        })
        return self.apply_declension(
            stem=self.stem,
            suffix=suffix,
        )

    @property
    def gen_sg(self):
        suffix = self.get_suffix({
            RussianGender.M: {
                RussianNounSuffix.M_C: "а",
                RussianNounSuffix.M_JI: "я",
                RussianNounSuffix.M_S: "я",
            },
            RussianGender.F: {
                RussianNounSuffix.F_A: "ы",
                RussianNounSuffix.F_JA: "и",
                RussianNounSuffix.F_S: "и",
            },
            RussianGender.N: {
                RussianNounSuffix.N_O: "а",
                RussianNounSuffix.N_JE: "я",
            },
        })
        return self.apply_declension(
            stem=self.stem,
            suffix=suffix,
        )

    @property
    def gen_pl(self):
        suffix = self.get_suffix({
            RussianGender.M: {
                RussianNounSuffix.M_C: "ов" if self._bare[-2] not in "шжщч" else "ей",
                RussianNounSuffix.M_JI: "ев",
                RussianNounSuffix.M_S: "ей",
            },
            RussianGender.F: {
                RussianNounSuffix.F_A: "",
                RussianNounSuffix.F_JA: "ей" if self._bare[-2] != "и" else "й",
                RussianNounSuffix.F_S: "ей",
            },
            RussianGender.N: {
                RussianNounSuffix.N_O: "",
                RussianNounSuffix.N_JE: "ей" if self._bare[-2] != "и" else "й",
            },
        })
        return self.apply_declension(
            stem=self.stem,
            suffix=suffix,
        )

    @property
    def dat_sg(self):
        suffix = self.get_suffix({
            RussianGender.M: {
                RussianNounSuffix.M_C: "у",
                RussianNounSuffix.M_JI: "ю",
                RussianNounSuffix.M_S: "ю",
            },
            RussianGender.F: {
                RussianNounSuffix.F_A: "е",
                RussianNounSuffix.F_JA: "е" if self._bare[-2] != "и" else "и",
                RussianNounSuffix.F_S: "и",
            },
            RussianGender.N: {
                RussianNounSuffix.N_O: "у",
                RussianNounSuffix.N_JE: "ю",
            },
        })
        return self.apply_declension(
            stem=self.stem,
            suffix=suffix,
        )

    @property
    def dat_pl(self):
        suffix = self.get_suffix({
            RussianGender.M: {
                RussianNounSuffix.M_C: "ам",
                RussianNounSuffix.M_JI: "ям",
                RussianNounSuffix.M_S: "ям",
            },
            RussianGender.F: {
                RussianNounSuffix.F_A: "ам",
                RussianNounSuffix.F_JA: "ям",
                RussianNounSuffix.F_S: "ям",
            },
            RussianGender.N: {
                RussianNounSuffix.N_O: "ам",
                RussianNounSuffix.N_JE: "ям",
            },
        })
        return self.apply_declension(
            stem=self.stem,
            suffix=suffix,
        )

    @property
    def acc_sg(self):
        if self.gender == RussianGender.M:
            if not self.is_animate:
                return self.nom_sg
            else:
                return self.gen_sg

        elif self.gender == RussianGender.F:
            suffix = self.get_suffix({
                RussianGender.F: {
                    RussianNounSuffix.F_A: "у",
                    RussianNounSuffix.F_JA: "ю",
                    RussianNounSuffix.F_S: "ь",
                },
            })
            return self.apply_declension(
                stem=self.stem,
                suffix=suffix,
            )

        else:
            return self.nom_sg

    @property
    def acc_pl(self):
        if self.gender in (RussianGender.M, RussianGender.F):
            if not self.is_animate:
                return self.nom_pl
            else:
                return self.gen_pl

        else:
            return self.nom_pl

    @property
    def inst_sg(self):
        suffix = self.get_suffix({
            RussianGender.M: {
                RussianNounSuffix.M_C: "ом",
                RussianNounSuffix.M_JI: "ем",
                RussianNounSuffix.M_S: "ем",
            },
            RussianGender.F: {
                RussianNounSuffix.F_A: "ой",
                RussianNounSuffix.F_JA: "ей",
                RussianNounSuffix.F_S: "ью",
            },
            RussianGender.N: {
                RussianNounSuffix.N_O: "ом",
                RussianNounSuffix.N_JE: "ем",
            },
        })
        return self.apply_declension(
            stem=self.stem,
            suffix=suffix,
        )

    @property
    def inst_pl(self):
        suffix = self.get_suffix({
            RussianGender.M: {
                RussianNounSuffix.M_C: "ами",
                RussianNounSuffix.M_JI: "ями",
                RussianNounSuffix.M_S: "ями",
            },
            RussianGender.F: {
                RussianNounSuffix.F_A: "ами",
                RussianNounSuffix.F_JA: "ями",
                RussianNounSuffix.F_S: "ями",
            },
            RussianGender.N: {
                RussianNounSuffix.N_O: "ами",
                RussianNounSuffix.N_JE: "ями",
            },
        })
        return self.apply_declension(
            stem=self.stem,
            suffix=suffix,
        )

    @property
    def prep_sg(self):
        suffix = self.get_suffix({
            RussianGender.M: {
                RussianNounSuffix.M_C: "е",
                RussianNounSuffix.M_JI: "е",
                RussianNounSuffix.M_S: "е",
            },
            RussianGender.F: {
                RussianNounSuffix.F_A: "е",
                RussianNounSuffix.F_JA: "е" if self._bare[-2] != "и" else "и",
                RussianNounSuffix.F_S: "и",
            },
            RussianGender.N: {
                RussianNounSuffix.N_O: "е",
                RussianNounSuffix.N_JE: "е" if self._bare[-2] != "и" else "и",
            },
        })
        return self.apply_declension(
            stem=self.stem,
            suffix=suffix,
        )

    @property
    def prep_pl(self):
        suffix = self.get_suffix({
            RussianGender.M: {
                RussianNounSuffix.M_C: "ах",
                RussianNounSuffix.M_JI: "ях",
                RussianNounSuffix.M_S: "ях",
            },
            RussianGender.F: {
                RussianNounSuffix.F_A: "ах",
                RussianNounSuffix.F_JA: "ях",
                RussianNounSuffix.F_S: "ях",
            },
            RussianGender.N: {
                RussianNounSuffix.N_O: "ах",
                RussianNounSuffix.N_JE: "ях",
            },
        })
        return self.apply_declension(
            stem=self.stem,
            suffix=suffix,
        )