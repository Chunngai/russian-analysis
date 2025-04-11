from typing import List

from tqdm import tqdm

from IO import (
    read_tokens, 
    read_csv, 
    write_csv
)
from russian_gender import RussianGender
from noun_analyses.russian_noun import (
    RussianNoun, 
    RussianNounDeclensionType, 
    RUSSIAN_NOUN_DECLENSION_TYPES
)
from utils import (
    remove_accent_mark, 
    supplement_accent_mark, 
    eval_boolean, 
    get_ground_truth_declension_forms, 
    get_rule_based_declension_form, 
    get_irregular_declension_indices, 
    get_accent_change_indices, 
    irregular_declension_key, 
    Irregular_declension_key, 
    accent_change_key, 
    multiple_variants_key,
    get_bits_str_and_tags
)


def get_nom_sg_ids(tokens, words, words_forms):
    
    token_set = set(tokens)

    nom_sg_ids = set()

    for row in tqdm(words):
        if row["type"] != "noun":
            continue
        if row["bare"] not in token_set:
            continue

        nom_sg_ids.add(row["id"])

    for row in tqdm(words_forms):
        if not row["form_type"].startswith("ru_noun_"):
            continue
        if row["_form_bare"] not in token_set:
            continue

        nom_sg_ids.add(row["word_id"])

    print(f"#nom_sg_ids: {len(nom_sg_ids):,}")

    return nom_sg_ids


def get_noun_analyses(nom_sg_ids, nouns, words, words_forms, translations):

    noun_analyses = {}

    # Get bare, accented and usage from `words`.
    for row in tqdm(words):
        if not row["id"] in nom_sg_ids:
            continue

        noun_analyses[row["id"]] = {
            "bare": row["bare"],
            "accented": supplement_accent_mark(row["accented"]),
            "meta": {
                "usage": row["usage_en"]
            }
        }

    # Get meta from `nouns`.
    for row in tqdm(nouns):
        if row["word_id"] not in nom_sg_ids:
            continue

        for k, v in row.items():
            if k == "word_id":
                continue
            noun_analyses[row["word_id"]]["meta"][k] = v

    # Get translations from `translations`.
    for row in tqdm(translations):
        if not row["word_id"] in nom_sg_ids:
            continue
        if not row["lang"] == "en":
            continue

        noun_analyses[row["word_id"]]["meta"].setdefault(
            "translations", 
            []
        ).append(row["tl"].strip())

    # Get ground-truth declensions from `words_forms`.
    for row in tqdm(words_forms):
        if row["word_id"] not in nom_sg_ids:
            continue

        noun_analyses[row["word_id"]].setdefault(
            "ground_truth_decls",
            {}
        ).setdefault(
            "_".join(list(reversed(row["form_type"].replace(
                "ru_noun_",
                "",
            ).split("_")))),
            []
        ).append({
            "position": row["position"],
            "bare": row["_form_bare"],
            "accented": supplement_accent_mark(row["form"]),
        })

    print(f"#nom_sg_info: {len(noun_analyses):,}")

    return noun_analyses


def fix_noun_analyses(noun_analyses):

    nouns_to_remove = []
    for nom_sg_id, d in noun_analyses.items():

        if d["bare"] == "менеджер":
            d["meta"]["animate"] = "1"

        if d["bare"] == "использование":
            d["ground_truth_decls"]["inst_sg"][0]["accented"] = "испо'льзованием"
        if d["bare"] == "жизнь":
            d["ground_truth_decls"]["prep_sg"][0]["accented"] = "жи'зни"
        if d["bare"] == "голубь":
            d["ground_truth_decls"]["nom_sg"][0]["accented"] = "го'лубь"
        if d["bare"] == "фотоаппарат":
            d["ground_truth_decls"]["inst_sg"][0]["accented"] = "фотоаппара'том"
        if d["bare"] == "логин":
            d["accented"] = "логи'н"
        if d["bare"] == "стих" and d["accented"] == "стих'":
            d["accented"] = "сти'х"

        if d["bare"] in ["министр", "президент"]:
            d["ground_truth_decls"]["acc_sg"] = d["ground_truth_decls"]["gen_sg"]
            d["ground_truth_decls"]["acc_pl"] = d["ground_truth_decls"]["gen_pl"]

        if d["bare"] == "флéшка":
            d["bare"] = "флешка"
            d["accented"] = "фле'шка"
            for decl_type in RUSSIAN_NOUN_DECLENSION_TYPES:
                d["ground_truth_decls"][decl_type][0]["accented"] = d["ground_truth_decls"][decl_type][0]["accented"].replace(
                    "е́",
                    "е'"
                )

        if d["bare"] == "MP3-плеер":
            for decl_type in RUSSIAN_NOUN_DECLENSION_TYPES:
                d["ground_truth_decls"][decl_type][0]["accented"] = "MP3-" + d["ground_truth_decls"][decl_type][0]["accented"]
            d["ground_truth_decls"]["gen_sg"][0]["accented"] = "MP3-пле'ера"

        if (
            "translations" not in d["meta"] 
            or (
                "translations" in d["meta"] 
                and len(d["meta"]["translations"]) == 0
            )
        ):
            nouns_to_remove.append(nom_sg_id)
            print(f"Removing {d['bare']}/{d['accented']} ({nom_sg_id}) as it has not translations.")

    for nom_sg_id in nouns_to_remove:
        del noun_analyses[nom_sg_id]

    return noun_analyses


def apply_declensions(russian_noun):

    decls = {}
    for decl_type in RUSSIAN_NOUN_DECLENSION_TYPES:
        decl = eval(f"russian_noun.{decl_type}")
        decls[decl_type] = decl

    return decls


def make_row(d):

    row = dict(
        bare_form=d["bare"],
        accented_form=d["accented"],
        # Meta info.
        last_letter=d["bare"][-1],
        gender=d["meta"]["gender"],
        translations="; ".join(d["meta"].get("translations", "")),
        is_animate=eval_boolean(d["meta"]["animate"]),
        is_indeclinable=eval_boolean(d["meta"]["indeclinable"]),
        is_sg_only=eval_boolean(d["meta"]["sg_only"]),
        is_pl_only=eval_boolean(d["meta"]["pl_only"]),
        partner=d["meta"]["partner"],
        usage=d["meta"]["usage"],
    )
    
    # Make tags.

    irreg_decl_tags = []
    Irreg_decl_tags = []  # Not counting -а/-у (e.g., по'та/по'ту) in gen_sg and -у' (саду'/са'де) in prep_sg.
    accent_chg_tags = []
    multi_vars_tags = []
    
    for decl_type in RUSSIAN_NOUN_DECLENSION_TYPES:
        
        ground_truth_decl_forms = get_ground_truth_declension_forms(d, decl_type)
        row[decl_type] = "/".join(ground_truth_decl_forms)

        rule_based_decl_form = get_rule_based_declension_form(d, decl_type)

        irregular_declension_indices = get_irregular_declension_indices(
            ground_truth_decl_forms,
            rule_based_decl_form,
        )
        accent_change_indices = get_accent_change_indices(
            ground_truth_decl_forms,
            rule_based_decl_form,
        )

        # Fix о'м/ем in m.inst_sg..
        if (
            decl_type == RussianNounDeclensionType.INST_SG
            and d["meta"]["gender"] == RussianGender.M
            and len(irregular_declension_indices) >=1
        ):
            for i, ground_truth_decl_form in enumerate(ground_truth_decl_forms):
                gt = remove_accent_mark(ground_truth_decl_form)
                rb = remove_accent_mark(rule_based_decl_form)
                if (
                    len(gt) > 3
                    and len(rb) > 3
                    and gt[:-2] == rb[:-2]  # The stem is identical.
                    and gt[-3] in "шжщчц"
                    and set((
                        gt[-2:],
                        rb[-2:],
                    )) == {"ом", "ем"}
                ):
                    print("Fixing о'м/ем in m.inst_sg:", d["accented"], ground_truth_decl_form, rule_based_decl_form)
                    irregular_declension_indices.remove(i)

        # Fix -ою/-ёю/-ею in f.inst_sg.
        if (
            decl_type == RussianNounDeclensionType.INST_SG 
            and d["meta"]["gender"] == RussianGender.F
            and len(ground_truth_decl_forms) >= 1
        ):
            for i, ground_truth_decl_form in enumerate(ground_truth_decl_forms):
                if remove_accent_mark(ground_truth_decl_form)[-2:] in (
                    "ою",
                    "ёю",
                    "ею"
                ) and i in irregular_declension_indices:
                    print("Fixing -ою/-ёю/-ею in f.inst_sg:", d["accented"], ground_truth_decl_form)
                    irregular_declension_indices.remove(i)

        Irregular_declension_indices = irregular_declension_indices[:]

        # Not counting -а/-у (e.g., по'та/по'ту) in gen_sg.
        if (
            decl_type == RussianNounDeclensionType.GEN_SG
            and len(ground_truth_decl_forms) == 2
            and set(list(map(
                lambda f: remove_accent_mark(f)[-1],
                ground_truth_decl_forms
            ))) == {"а", "у"}
        ):
            for i, ground_truth_decl_form in enumerate(ground_truth_decl_forms):
                if remove_accent_mark(ground_truth_decl_form)[-1] == "у":
                    print(f"Setting as not Irregular for gen_sg of {d['bare']} ({ground_truth_decl_forms})")
                    Irregular_declension_indices.remove(i)
                    break
        
        # Not counting -у' (саду'/са'де) in prep_sg.
        if (
            decl_type == RussianNounDeclensionType.PREP_SG
            and len(ground_truth_decl_forms) == 2
            and set(list(map(
                lambda f: remove_accent_mark(f)[-1],
                ground_truth_decl_forms
            ))) == {"е", "у"}
        ):
            for i, ground_truth_decl_form in enumerate(ground_truth_decl_forms):
                if remove_accent_mark(ground_truth_decl_form)[-1] == "у":
                    print(f"Setting as not Irregular for prep_sg of {d['bare']} ({ground_truth_decl_forms})")
                    Irregular_declension_indices.remove(i)
                    break

        irregular_declension_indices.sort()
        Irregular_declension_indices.sort()
        accent_change_indices.sort()

        mapping = {}   

        if len(irregular_declension_indices) >= 1:
            mapping[irregular_declension_key] = ":".join(list(map(
                str,
                irregular_declension_indices,
            )))
        if len(Irregular_declension_indices) >= 1:
            mapping[Irregular_declension_key] = ":".join(list(map(
                str,
                Irregular_declension_indices,
            )))

        if len(accent_change_indices) >= 1:
            mapping[accent_change_key] = ":".join(list(map(
                str,
                accent_change_indices,
            )))

        has_multiple_variants = len(ground_truth_decl_forms) > 1
        if has_multiple_variants:
            mapping[multiple_variants_key] = True

        (
            bits_str,
            tags
        ) = get_bits_str_and_tags(
            wrapped = [
                (irregular_declension_key, irreg_decl_tags, "i"), 
                (Irregular_declension_key, Irreg_decl_tags, "I"), 
                (accent_change_key, accent_chg_tags, "a"), 
                (multiple_variants_key, multi_vars_tags, "m")
            ],
            mapping=mapping,
            conjugation_name=decl_type,
        )
        row[f"{decl_type}_tags"] = bits_str + ", ".join(tags)

    for k in [
        irregular_declension_key,
        Irregular_declension_key,
        accent_change_key, 
        multiple_variants_key
    ]:
        row[k] = ",".join(eval(f"{k}_tags"))

    return row


def main(tokens: List[str], nouns: List[dict], words: List[dict], words_forms: List[dict], translations: List[dict], fp_analyses: str):
    """Analyze nouns.

    Output file format:

        bare_form, accented_form, last_letter, gender, translations, is_animate, is_indeclinable, is_sg_only, is_pl_only, partner, usage,
        nom_sg, nom_sg_tags, nom_pl, nom_pl_tags,
        gen_sg, gen_sg_tags, gen_pl, gen_pl_tags,
        dat_sg, dat_sg_tags, dat_pl, dat_pl_tags,
        acc_sg, acc_sg_tags, acc_pl, acc_pl_tags,
        inst_sg, inst_sg_tags, inst_pl, inst_pl_tags,
        prep_sg, prep_sg_tags, prep_pl, prep_pl_tags,
        irreg_decl, Irreg_decl, accent_chg, multi_vars

    Tags of each declension type includes

        1. irregular_declension (irreg_decl)
        2. irregular_declension tot counting -а/-у (e.g., по'та/по'ту) in gen_sg and -у' (саду'/са'де) in prep_sg. (Irreg_decl)
        3. accent_change (accent_chg)
        4. multiple_variants (multi_vars)

    Steps:

        1. Get all noun tokens from `tokens`.
        2. Get all nom sgs from the noun tokens.
            I.e., for each noun token, if it is a nom sg, do nothing, else get its nom sg.
        3. For each nom sg:
            a. Get its bare and accented forms.
            b. Get its meta info (e.g., gender, partner, animate, etc.).
            c. Get its ground-truth declensions.
            d. Perform declensions according to the Russian noun declension rules and
                compare the declensions with the ground truth. Mark all inconsistent declensions with
                decl_tags.

    """

    nom_sg_ids = get_nom_sg_ids(
        tokens=tokens,
        words=words,
        words_forms=words_forms,
    )

    noun_analyses = get_noun_analyses(
        nom_sg_ids=nom_sg_ids,
        words=words,
        nouns=nouns,
        words_forms=words_forms,
        translations=translations,
    )
    noun_analyses = fix_noun_analyses(
        noun_analyses
    )

    rows = []  # For storing.
    for _, d in noun_analyses.items():
        
        russian_noun = RussianNoun(
            accented=d["accented"],
            gender=d["meta"]["gender"],
            is_animate=eval_boolean(d["meta"]["animate"]),
        )
        d["rule_based_decls"] = apply_declensions(russian_noun)

        row = make_row(d)
        rows.append(row)

    write_csv(
        fp=fp_analyses,
        l=list(sorted(
            rows,
            key=lambda r: r["bare_form"]
        )),
    )
    # write_csv(
    #     fp="noun_analyses.tagged.csv",
    #     l=list(sorted(
    #         rows,
    #         key=lambda row: row["tag_sequence"]
    #     )),
    # )
    # write_csv(
    #     fp="noun_analyses.tagged.csv",
    #     l=list(sorted(
    #         list(filter(
    #             bool,
    #             list(map(
    #                 lambda row: (
    #                     row
    #                     if any(list(map(
    #                         lambda decl_type: len(row[f"{decl_type}_tags"]) != 0,
    #                         RUSSIAN_NOUN_DECLENSION_TYPES,
    #                     )))
    #                     else None
    #                 ),
    #                 rows,
    #             ))
    #         )),
    #         key=lambda row: (
    #             row["gender"], 
    #             # row["bare_form"][-1], 
    #             "/".join(list(map(
    #                 lambda decl_type: ",".join(list(map(
    #                     lambda tag: (
    #                         tag
    #                         if "accent_change" in tag
    #                         else "-"
    #                     ),
    #                     row[f"{decl_type}_tags"]
    #                 ))),
    #                 RUSSIAN_NOUN_DECLENSION_TYPES
    #             ))),
    #             "/".join(list(map(
    #                 lambda decl_type: ",".join(list(map(
    #                     lambda tag: (
    #                         tag
    #                         if "irregular_declension" in tag
    #                         else "-"
    #                     ),
    #                     row[f"{decl_type}_tags"]
    #                 ))),
    #                 RUSSIAN_NOUN_DECLENSION_TYPES
    #             ))),
    #         ),
    #     ))
    # )

    # print(noun_analyses)


if __name__ == '__main__':
    tokens = read_tokens(
        fp_words="uploads/words.ru.json",
        fp_articles="uploads/articles.ru.json",
        duolingo_only_articles=True,
    )
    print(f"#tokens: {len(tokens):,}")

    nouns = read_csv(fp="russian_word_analyses/resources/nouns.csv")
    words = read_csv(fp="russian_word_analyses/resources/words.csv")  # Nouns in `words` are infinitives.
    words_forms = read_csv(fp="russian_word_analyses/resources/words_forms.csv")
    translations = read_csv(fp="russian_word_analyses/resources/translations.csv")
    print(
        f"#nouns: {len(nouns):,}, "
        f"#words: {len(words):,}, "
        f"#words_forms: {len(words_forms):,}, "
        f"#translations: {len(translations):,}"
    )

    fp_analyses = "russian_word_analyses/files/noun_analyses.csv"
    main(
        tokens=tokens,
        nouns=nouns,
        words=words,
        words_forms=words_forms,
        translations=translations,
        fp_analyses=fp_analyses,
    )
