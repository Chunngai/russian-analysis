import csv
import hashlib
import json
import os.path
import string
from tqdm import tqdm
from typing import List, Dict, Tuple, Optional

accent_mark = "'"

special_case_mark = "*"
accent_pos_changing_mark = "'"
undetermined_mark = "?"

vowels = "аеёиоуыэюя"
labial_consonants = "бвпмф"
jaju_special_consonants = "жшщч"


def read_json(fp: str) -> dict:
    with open(fp, encoding="utf-8") as f:
        j = json.load(f)
    return j


def save_json(d: dict, fp: str):
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(
            obj=d,
            fp=f,
            ensure_ascii=False,
            indent=2,
        )


def read_tokens(fp_words: Optional[str], fp_articles: Optional[str]) -> List[str]:
    tokens = []

    if fp_words is not None:
        for d in read_json(fp=fp_words):
            tokens.extend(d["text"].strip().split())

    if fp_articles is not None:
        for d in read_json(fp=fp_articles):
            for para in d["paras"]:
                tokens.extend(para["text"].strip().split())

    letters_to_strip = (
            " "
            + string.punctuation
            + string.digits
            + string.ascii_letters
            + "«»–—ー"
    )
    tokens = list(sorted(set(map(
        lambda token: token.lower().strip(letters_to_strip),
        tokens
    ))))
    return tokens


def read_csv(fp: str) -> List[dict]:
    with open(fp, "r", encoding="utf-8") as f:
        csv_reader = csv.DictReader(f)
        return list(csv_reader)


def write_csv(fp: str, l: List[dict]):
    with open(fp, "w", encoding="utf-8") as f:
        csv_writer = csv.DictWriter(f, fieldnames=list(l[0].keys()))
        csv_writer.writeheader()
        csv_writer.writerows(l)


def add_accent_mark_for_word_with_single_vowel(word: str) -> str:
    def is_word_with_single_vowel(word: str) -> bool:
        count = 0
        for char in word:
            if char in vowels:
                count += 1
                if count > 1:
                    return False
        return True

    def get_first_vowel_position(word: str) -> Optional[int]:
        for i, char in enumerate(word):
            if char in vowels:
                return i
        return None

    # Already has an accent mark.
    if accent_mark in word:
        return word

    # E.g., щёлкать: 2.
    if "ё" in word:
        accent_pos = word.index("ё") + 1
        return word[:accent_pos] + accent_mark + word[accent_pos:]

    # Cannot determine the position of the accent mark,
    # so skip.
    if not is_word_with_single_vowel(word):
        return word

    vowel_pos = get_first_vowel_position(word)
    if vowel_pos is None:
        return word

    word = (
            word[:vowel_pos + 1]
            + accent_mark
            + word[vowel_pos + 1:]
    )
    return word


def remove_accent_mark(word: str) -> str:
    return word.replace(
        accent_mark,
        "",
    )


def analyze_verbs(tokens, verbs, words, words_forms, fp_token2inf_ids, fp_analyses):
    """Fields:
    infinitive, accented_infinitive,
    stem, suffix,
    aspect, partners,
    conjugation_type,
    present/future forms ...,
    imperative forms ...,
    past forms ...
    """

    ###### Constants ######

    # Conjugation types.
    je_conj = "е-conj"
    ji_conj = "и-conj"
    #
    jesh_ = "ешь"
    josh_ = "ёшь"
    jish_ = "ишь"

    # Suffices.
    t_ = "ть"
    tji = "ти"
    ch_ = "чь"
    #
    sja_ = "ся"
    s_ = "сь"
    #
    a = "а"
    ja = "я"
    je = "е"
    ji = "и"
    u = "у"
    y = "ы"

    # Aspects.
    ipfv = "imperfective"
    pfv = "perfective"

    present_form_types = [
        "ru_verb_presfut_sg1",
        "ru_verb_presfut_sg2",
        "ru_verb_presfut_sg3",
        "ru_verb_presfut_pl1",
        "ru_verb_presfut_pl2",
        "ru_verb_presfut_pl3",
    ]
    imperative_form_types = [
        "ru_verb_imperative_sg",
        "ru_verb_imperative_pl",
    ]
    past_form_types = [
        "ru_verb_past_m",
        "ru_verb_past_f",
        "ru_verb_past_n",
        "ru_verb_past_pl",
    ]
    all_form_types = (
            present_form_types
            + imperative_form_types
            + past_form_types
    )

    ###### Constants ######

    print("Constructing id2verb")
    id2verb = {
        verb["word_id"]: verb
        for verb in tqdm(verbs)
    }
    print("Constructing id2word")
    id2word = {
        word["id"]: word
        for word in tqdm(words)
    }
    print("Constructing id2wordforms")
    id2word_forms = {}
    for wf in tqdm(words_forms):
        id2word_forms.setdefault(wf["word_id"], {})
        id2word_forms[wf["word_id"]][wf["form_type"]] = wf

    def get_token2inf_ids() -> Dict[str, List[str]]:
        """token: [infinitive_ids]"""

        # For saving time.
        if os.path.exists(fp_token2inf_ids):
            token2inf_ids = read_json(fp=fp_token2inf_ids)
            return token2inf_ids

        print("Constructing token2inf_ids.")

        token2inf_ids = {}

        # Each verb in `words` is inf,
        # so this loop mainly constructs inf: [{inf_id:accented_inf:}].
        for w in tqdm(words):

            token = w["bare"]
            if token not in tokens:  # Check this first to save time.
                continue

            if w["type"] != "verb":
                continue

            if token not in token2inf_ids.keys():
                token2inf_ids[token] = []

            inf_id = w["id"]
            if inf_id not in token2inf_ids[token]:
                token2inf_ids[token].append(inf_id)

        # Each verb in `words_forms` is a specific form of a verb,
        # so this loop mainly constructs verb: [{inf_id:accented_inf:}].
        for wf in tqdm(words_forms):

            token = wf["_form_bare"]
            if token not in tokens:
                continue

            if not wf["form_type"].startswith("ru_verb"):
                continue

            if token not in token2inf_ids.keys():
                token2inf_ids[token] = []

            inf_id = wf["word_id"]
            if inf_id not in token2inf_ids[token]:
                token2inf_ids[token].append(inf_id)

        save_json(
            d=token2inf_ids,
            fp=fp_token2inf_ids,
        )

        return token2inf_ids

    token2inf_ids = get_token2inf_ids()

    def get_stem_and_suffix(infinitive: str) -> Tuple[Optional[str], Optional[str]]:

        infinitive = remove_accent_mark(word=infinitive)

        has_sja_ = False
        if infinitive[-2:] == sja_:
            has_sja_ = True
            infinitive = infinitive[:-2]

        stem, suffix = infinitive[:-2], infinitive[-2:]
        if stem[-1] in [a, ja, je, ji, u, y] and suffix == t_:
            pass
        elif suffix in [tji, ch_]:
            pass
        else:
            print(
                f"[error] split_infinitive(): "
                f"Failed to split the infinitive {infinitive}."
            )
            return undetermined_mark, undetermined_mark

        if has_sja_:
            suffix += sja_

        return stem, suffix

    def get_conjugation_type(infinitive: str, presfut_sg2: str) -> Optional[str]:

        infinitive = remove_accent_mark(word=infinitive)
        if infinitive[-2:] == sja_:
            infinitive = infinitive[:-2]  # Remove sja_.
        infinitive_stem = infinitive[:-2]  # Remove suffix.

        presfut_sg2 = remove_accent_mark(word=presfut_sg2)
        if presfut_sg2[-2:] == sja_:
            presfut_sg2 = presfut_sg2[:-2]  # Remove sja_.
        presfut_sg2_suffix = presfut_sg2[-3:]  # Remove jesh_/josh_.

        if presfut_sg2_suffix in [jesh_, josh_]:
            conj_type = je_conj
            # Special case.
            if infinitive_stem[-1] == ji:
                conj_type = f"{special_case_mark}{conj_type}"
        elif presfut_sg2_suffix in [jish_]:
            conj_type = ji_conj
            # Special case.
            if infinitive_stem[-1] != ji:
                conj_type = f"{special_case_mark}{conj_type}"
        else:
            print(
                f"[error] get_conjugation_type(): "
                f"Failed to detect the conjugation type for {infinitive}.")
            conj_type = undetermined_mark

        return conj_type

    """Present/future special cases
    For е-conj verbs:
    (1) Verbs ending in "авать" (e.g., давать): remove "вать" and add suffices.
    (2) Verbs ending in "о/евать" (e.g., здравствовать, танцевать): remove "о/евать", add "у" and add suffices.
    (3) Few verbs ending in "еть" or "ить" (e.g., жить, петь) belongs to е-conj verbs, and "о", "е" or a consonant 
        may be required in their conjugations.
    (4) When ending in "а/и/еть", some consonants before these suffices may be changed for all forms: 
        "г/д/з" -> "ж", "к/т" -> "ч", "х/с" -> "ш", "ст/ск" -> "щ". 
    For и-conj verbs:
    (1) When ending in "а/и/еть", some consonants before these suffices may be changed for the presfut_sg1 form: 
        "г/д/з" -> "ж", "к/т" -> "ч", "х/с" -> "ш", "ст/ск" -> "щ". 
    """

    def ru_verb_presfut_sg1(stem: str, suffix: str, accent_pos: int, conjugation_type: str):

        if conjugation_type == je_conj:
            if stem[-1] in vowels:
                return stem + "ю"
            else:
                return stem + "у"

        elif conjugation_type == ji_conj:
            if stem[-2] not in jaju_special_consonants:
                if stem[-2] not in labial_consonants:
                    return stem[:-1] + "ю"
                else:
                    # If the accent pos is at the end of the stem,
                    # it should be updated by adding one.
                    # E.g., люби'-ть (accent_pos == 4) ->люб-лю' (accent_pos = 5).
                    if accent_pos == len(stem):
                        accent_pos += 1
                    return stem[:-1] + "лю", accent_pos

            else:
                return stem[:-1] + "у"

        return undetermined_mark

    def ru_verb_presfut_sg2(stem: str, suffix: str, accent_pos: int, conjugation_type: str):

        if conjugation_type == je_conj:
            if accent_pos != len(stem) + 1:
                return stem + "ешь"
            else:
                return stem + "ёшь"

        elif conjugation_type == ji_conj:
            return stem[:-1] + "ишь"

        return undetermined_mark

    def ru_verb_presfut_sg3(stem: str, suffix: str, accent_pos: int, conjugation_type: str):

        if conjugation_type == je_conj:
            if accent_pos != len(stem) + 1:
                return stem + "ет"
            else:
                return stem + "ёт"

        elif conjugation_type == ji_conj:
            return stem[:-1] + "ит"

        return undetermined_mark

    def ru_verb_presfut_pl1(stem: str, suffix: str, accent_pos: int, conjugation_type: str):

        if conjugation_type == je_conj:
            if accent_pos != len(stem) + 1:
                return stem + "ем"
            else:
                return stem + "ём"

        elif conjugation_type == ji_conj:
            return stem[:-1] + "им"

        return undetermined_mark

    def ru_verb_presfut_pl2(stem: str, suffix: str, accent_pos: int, conjugation_type: str):

        if conjugation_type == je_conj:
            if accent_pos != len(stem) + 1:
                return stem + "ете"
            else:
                return stem + "ёте"

        elif conjugation_type == ji_conj:
            return stem[:-1] + "ите"

        return undetermined_mark

    def ru_verb_presfut_pl3(stem: str, suffix: str, accent_pos: int, conjugation_type: str):

        if conjugation_type == je_conj:
            if stem[-1] in vowels:
                return stem + "ют"
            else:
                return stem + "ут"

        elif conjugation_type == ji_conj:
            if stem[-2] not in jaju_special_consonants:
                return stem[:-1] + "ят"
            else:
                return stem[:-1] + "ат"

        return undetermined_mark

    """Imperative special cases:
    (1) when the stem starts with an accented "вы" (e.g., вы'йти), the ending is "и".
    (2) ipfv ending in "авать" (e.g., давать): remove "ть" and add "й".
    (3) дать and prefix + дать (e.g., отдать): *дай.
    (4) ехать and prefix + ехать (e.g., приехать): *езжай.
    (5) есть and prefix + есть (e.g., съесть): *ешь.
    (6) je-conj single-vowel verbs ending with "и" (e.g., пить): *ей.
    (7) лечь: ляг.
    """

    def ru_verb_imperative_sg(stem: str, suffix: str, accent_pos: int, conjugation_type: str):

        # https://russianenthusiast.com/russian-grammar/verbs/imperative-mood/

        presfut_pl3_stem = ru_verb_presfut_pl3(
            stem=stem,
            suffix=suffix,
            conjugation_type=conjugation_type,
            accent_pos=accent_pos,
        )[:-2]  # дума-ют -> stem = дума.
        if len(presfut_pl3_stem) == 0:
            return undetermined_mark

        # Present-future plural3 stem ending with a vowel.
        if presfut_pl3_stem[-1] in vowels:
            return presfut_pl3_stem + "й"
        # (1) Present-future plural3 stem ending in a consonant.
        # (2) The я form is stressed on the ending (same as:
        # the infinitive is stressed on the first letter of the suffix.
        # The reason is that the accent pos of the я form is consistent with
        # that of the infinitive.)
        # In this condition, the accent lies on "и".
        # e.g., пис-а'ть:
        # (1) пиш-у'т -> stem = пиш (ending in a consonant).
        # (2) пис-а'ть (the infinitive is stressed on the first letter of the suffix, i.e., а.)
        # (As for the я form пиш-у', it is stressed on the ending)
        # Therefore, the imperative of пис-а'ть is пиши'.
        elif len(presfut_pl3_stem) + 1 == accent_pos:
            return presfut_pl3_stem + "и"
        # (1) Present-future plural3 stem ending in a consonant.
        # (2) The я form is not stressed on the ending (same as:
        # the infinitive is stressed on the first letter of the suffix.)
        # e.g., бро'с-ить:
        # (1) бро'с-ят -> stem = бро'с (ending in a consonant).
        # (2) бро'с-ить (the infinitive is not stressed on the first letter of the suffix, i.e., с.)
        else:
            return presfut_pl3_stem + "ь"

    def ru_verb_imperative_pl(stem: str, suffix: str, accent_pos: int, conjugation_type: str):
        return ru_verb_imperative_sg(
            stem=stem,
            suffix=suffix,
            conjugation_type=conjugation_type,
            accent_pos=accent_pos
        ) + "те"

    def ru_verb_past_m(stem: str, suffix: str, accent_pos: int, conjugation_type: str):
        return stem + "л"

    def ru_verb_past_f(stem: str, suffix: str, accent_pos: int, conjugation_type: str):
        return stem + "ла"

    def ru_verb_past_n(stem: str, suffix: str, accent_pos: int, conjugation_type: str):
        return stem + "ло"

    def ru_verb_past_pl(stem: str, suffix: str, accent_pos: int, conjugation_type: str):
        return stem + "ли"

    verb_info = {}
    for token in tokens:

        # Get infinitive id.
        inf_ids = token2inf_ids.get(token)
        if inf_ids is None:
            # print(f"[error] Cannot obtain infinitive ids for {token}. Skipping.")
            continue

        # TODO
        # print(f"Analyzing verb: {token}")

        if len(inf_ids) > 1:
            print(
                f"[error] analyze_verbs(): "
                f"Found more than one infinitive ids for \"{token}\": {inf_ids}. Skipping."
            )
            continue
        inf_id = inf_ids[0]

        # Get bare and accented infinitives.
        bare_inf = id2word[inf_id]["bare"]
        accented_inf = add_accent_mark_for_word_with_single_vowel(word=id2word[inf_id]["accented"])
        if accented_inf in verb_info.keys():
            # Analyzed, so skip.
            continue

        accent_pos = (
            accented_inf.index(accent_mark)
            if accent_mark in accented_inf
            else None
        )

        # Get stem and suffix.
        stem, suffix = get_stem_and_suffix(infinitive=bare_inf)

        # Get aspect.
        aspect = id2verb[inf_id]["aspect"]

        # Get partners
        partners = id2verb[inf_id]["partner"]

        # Get conjugation_type.
        try:
            presfut_sg2 = id2word_forms[inf_id]["ru_verb_presfut_sg2"]["_form_bare"]
        except KeyError:
            print(
                f"[error] analyze_verbs(): "
                f"Cannot obtain presfut_sg2 for analyzing the conjugation type of {bare_inf}."
            )
            conjugation_type = undetermined_mark
        else:
            conjugation_type = get_conjugation_type(
                infinitive=bare_inf,
                presfut_sg2=presfut_sg2,
            )

        # Get forms.
        forms = {}
        for form_type in all_form_types:
            try:
                trg = id2word_forms[inf_id][form_type]["form"]
            except KeyError:
                print(
                    f"[error] analyze_verbs(): "
                    f"Cannot construct {form_type} for {bare_inf}. Skipping."
                )
                forms[form_type] = undetermined_mark
                continue

            r = eval(form_type)(
                stem=stem,
                suffix=suffix[:-2] if suffix.endswith(sja_) else suffix,
                accent_pos=accent_pos,
                conjugation_type=conjugation_type.replace(special_case_mark, ""),
            )
            if type(r) == str:
                form = r
            else:  # type(r) == tuple
                form, accent_pos = r

            if suffix.endswith(sja_):
                if not remove_accent_mark(word=form)[-1] in vowels:
                    form = form + sja_
                else:
                    form = form + s_

            # Add the accent mark.
            form = form[:accent_pos] + accent_mark + form[accent_pos:]

            if form != trg:
                print(
                    f"{'[' + form_type + ']':<25} "
                    f"{accented_inf + ' (' + stem + '-' + suffix + ')':<50} "
                    f"{form}(✔) {trg}(❌)"
                )

                if remove_accent_mark(form) == remove_accent_mark(trg):
                    forms[form_type] = f"({accent_pos_changing_mark}) {trg}"
                else:
                    forms[form_type] = f"({special_case_mark}) {trg}"
            else:
                forms[form_type] = ""  # For brevity.

        verb_info[accented_inf] = {
            "infinitive": bare_inf, "accented_infinitive": accented_inf,
            "stem": stem, "suffix": suffix,
            "aspect": aspect, "partners": partners,
            "conjugation_type": conjugation_type,
        }
        for form_type, form in forms.items():
            verb_info[accented_inf][form_type] = form

    write_csv(
        fp=fp_analyses,
        l=list(verb_info.values()),
    )

    # # Reorder: imperfective, perfective, other.
    # reordered_verb_info = []
    # processed_accented_infinitives = set()
    # for accented_infinitive, d in verb_info.items():
    #     if d["aspect"] != ipfv:
    #         continue
    #
    #     partners = d["partners"].split(";")
    #     for partner in partners:
    #         for accented_infinitive_of_partner, d_of_partner in verb_info.items():
    #             if partner != remove_accent_mark(accented_infinitive_of_partner):
    #                 continue
    #
    #             if d_of_partner["aspect"] != pfv:
    #                 continue
    #
    #             if accented_infinitive not in processed_accented_infinitives:
    #                 reordered_verb_info.append(d)
    #                 processed_accented_infinitives.add(accented_infinitive)
    #
    #             if accented_infinitive_of_partner not in processed_accented_infinitives:
    #                 reordered_verb_info.append(d_of_partner)
    #                 processed_accented_infinitives.add(accented_infinitive_of_partner)
    #
    # for accented_infinitive, d in verb_info.items():
    #     if accented_infinitive not in processed_accented_infinitives:
    #         reordered_verb_info.append(d)
    #
    # write_csv(
    #     fp="resource/verb_info.csv",
    #     l=reordered_verb_info
    # )


def main():
    tokens = read_tokens(
        fp_words="uploads/words.ru.json",
        # fp_articles="uploads/articles.ru.json",
        fp_articles=None,
    )
    print(f"#tokens: {len(tokens):,}")

    # tokens_hash = hash(str(tokens))
    # Do not use the built-in hash(),
    # it will return diff values each time.
    tokens_hash = hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest()
    print(f"tokens hash: {tokens_hash}")

    verbs = read_csv(fp="resource/verbs.csv")
    words = read_csv(fp="resource/words.csv")  # Verbs in `words` are infinitives.
    words_forms = read_csv(fp="resource/words_forms.csv")
    print(
        f"#verbs: {len(verbs):,}, "
        f"#words: {len(words):,}, "
        f"#words_forms: {len(words_forms):,}"
    )

    analyze_verbs(
        tokens=tokens,
        verbs=verbs,
        words=words,
        words_forms=words_forms,
        fp_token2inf_ids=f"resource/token2inf_ids.{tokens_hash}.txt",
        fp_analyses=f"resource/verb_info.{tokens_hash}.csv",
    )


if __name__ == '__main__':
    main()
