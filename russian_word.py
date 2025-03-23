from utils import get_accent_pos, remove_accent_mark, insert_accent_mark, list_enum_values


class RussianWord:

    def __init__(self, accented: str):

        self.accented = accented

        self.accent_pos = get_accent_pos(accented)
        self.bare = remove_accent_mark(accented)

    def concat(self, stem: str, suffix: str):

        if suffix == "":
            return stem

        rule1_letters = "гкхшжщч"
        rule2_letters = "гкхшжщчц"
        rule3_letters = "шжщчц"

        if stem[-1] in rule1_letters and suffix[0] == "ы":
            suffix = "и" + suffix[1:]

        if stem[-1] in rule2_letters and suffix[0] == "я":
            suffix = "а" + suffix[1:]
        if stem[-1] in rule2_letters and suffix[0] == "ю":
            suffix = "у" + suffix[1:]

        if stem[-1] in rule3_letters and suffix[0] == "о" and self.accent_pos != len(self.stem):
            suffix = "е" + suffix[1:]

        return stem + suffix
    
    def apply_declension(self, stem, suffix):

        if suffix is None:
            return ""
        
        decl = insert_accent_mark(
            self.concat(
                stem=stem,
                suffix=suffix,
            ),
            self.accent_pos,
        )
        assert "ayeo" not in decl  # The decl should not contain English vowels.

        return decl