from typing import List

from tqdm import tqdm

from IO import (
    read_tokens, 
    read_csv, 
    write_csv
)
from russian_gender import RussianGender
from adjective_analyses.russian_adjective import (
    RussianAdjective, 
    RussianAdjectiveDeclensionType, 
    RUSSIAN_ADJECTIVE_DECLENSION_TYPES
)
from utils import (
    get_accent_pos,
    insert_accent_mark,
    remove_accent_mark, 
    supplement_accent_mark, 
    eval_boolean, 
    get_ground_truth_declension_forms, 
    get_rule_based_declension_form, 
    get_irregular_declension_indices, 
    get_accent_change_indices, 
    irregular_declension_key, 
    accent_change_key, 
    multiple_variants_key,
    get_bits_str_and_tags,
    RUSSIAN_REFLEXIVE_SUFFIX_CJA
)


def get_nom_m_ids(tokens, words, words_forms):
    
    token_set = set(tokens)

    nom_m_ids = set()

    for row in tqdm(words):
        if row["type"] != "adjective":
            continue
        if row["bare"] not in token_set:
            continue

        nom_m_ids.add(row["id"])

    for row in tqdm(words_forms):
        if not row["form_type"].startswith("ru_adj_"):
            continue
        if row["_form_bare"].strip() == "":
            continue
        if row["_form_bare"].strip() not in token_set:
            continue

        nom_m_ids.add(row["word_id"])

    print(f"#nom_m_ids: {len(nom_m_ids):,}")

    return nom_m_ids


def get_adjective_analyses(nom_m_ids, adjectives, words, words_forms, translations):

    adjective_analyses = {}

    # Get bare, accented and usage from `words`.
    for row in tqdm(words):
        if not row["id"] in nom_m_ids:
            continue

        adjective_analyses[row["id"]] = {
            "bare": row["bare"],
            "accented": supplement_accent_mark(row["accented"]),
            "meta": {
                "usage": row["usage_en"]
            }
        }

    # Get meta from `adjectives`.
    for row in tqdm(adjectives):
        if row["word_id"] not in nom_m_ids:
            continue

        for k, v in row.items():
            if k == "word_id":
                continue
            adjective_analyses[row["word_id"]]["meta"][k] = v

    # Get translations from `translations`.
    for row in tqdm(translations):
        if not row["word_id"] in nom_m_ids:
            continue
        if not row["lang"] == "en":
            continue

        adjective_analyses[row["word_id"]]["meta"].setdefault(
            "translations", 
            []
        ).append(row["tl"].strip())

    # Get ground-truth declensions from `words_forms`.
    for row in tqdm(words_forms):
        if row["word_id"] not in nom_m_ids:
            continue

        if not row["_form_bare"]:
            continue

        key_splits = row["form_type"].replace(
            "ru_adj_",
            "",
        ).split("_")
        if "short" not in row["form_type"]:
            key_splits = reversed(key_splits)
        key = "_".join(list(key_splits))

        adjective_analyses[row["word_id"]].setdefault(
            "ground_truth_decls",
            {}
        ).setdefault(
            key,
            []
        ).append({
            "position": row["position"],
            "bare": row["_form_bare"],
            "accented": supplement_accent_mark(row["form"]),
        })

    print(f"#m_nom_sg_info: {len(adjective_analyses)}")

    return adjective_analyses


def fix_adjective_analyses(adjective_analyses):

    delimiter_mapping = {
        "точный": "//", 
        "далёкий": "//", 
        "глупый": "//",
        "новый": " / "
    }

    adjectives_to_remove = []
    for nom_m_id, d in adjective_analyses.items():

        if d["bare"] == "рабочий":
            d["ground_truth_decls"]["nom_n"][0] = {
                "position": "1",
                "bare": "рабочее",
                "accented": "рабо'чее",
            }
            d["ground_truth_decls"]["acc_n"] = d["ground_truth_decls"]["nom_n"]

        if d["bare"] == "спокойный":
            d["ground_truth_decls"]["prep_f"] = [{
                "position": "1",
                "bare": "спокойной",
                "accented": "споко'йной",
            }] 

        if d["bare"] == "серьёзный":
            d["ground_truth_decls"]["comparative"] = [
                {
                    "position": "1",
                    "bare": "серьёзнее",
                    "accented": "серьё'знее",
                },
                {
                    "position": "2",
                    "bare": "серьёзней",
                    "accented": "серьё'зней",
                }
            ]

        if d["bare"] == "функциональный":
            d["ground_truth_decls"]["prep_m"][0] = {
                "position": "1",
                "bare": "функциональном",
                "accented": "функциона'льном",
            }
            d["ground_truth_decls"]["prep_f"][0] = {
                "position": "1",
                "bare": "функциональной",
                "accented": "функциона'льной",
            }
            d["ground_truth_decls"]["prep_n"] = d["ground_truth_decls"]["prep_m"]

        if d["bare"] in ["готовимый", "танцуемый"]:
            accent_pos = get_accent_pos(d["accented"])
            for decl_type in RUSSIAN_ADJECTIVE_DECLENSION_TYPES:
                if decl_type not in d["ground_truth_decls"]:
                    continue
                for decl_form in d["ground_truth_decls"][decl_type]:
                    decl_form["accented"] = insert_accent_mark(
                        word=remove_accent_mark(decl_form["accented"]),
                        accent_pos=accent_pos,
                    )

        if d["bare"] == "украинский":
            accent_pos = get_accent_pos(d["accented"])
            for decl_type in RUSSIAN_ADJECTIVE_DECLENSION_TYPES:
                if decl_type not in d["ground_truth_decls"]:
                    continue
                for decl_form in d["ground_truth_decls"][decl_type]:
                    decl_form["accented"] = insert_accent_mark(
                        word=remove_accent_mark(decl_form["accented"]),
                        accent_pos=accent_pos,
                    )
            d["ground_truth_decls"]["inst_f"][1]["bare"] = "(украинскою)"
            d["ground_truth_decls"]["inst_f"][1]["accented"] = "(украи'нскою)"

        if d["bare"] == "арестованный":
            for decl_form in d["ground_truth_decls"]["acc_m"]:
                if decl_form["bare"] == "ного":
                    decl_form["bare"] = "арестованного"
                    decl_form["accented"] = "аресто'ванного"
            for decl_form in d["ground_truth_decls"]["acc_pl"]:
                if decl_form["bare"] == "ных":
                    decl_form["bare"] = "арестованных"
                    decl_form["accented"] = "аресто'ванных"
            for decl_form in d["ground_truth_decls"]["inst_f"]:
                if decl_form["bare"] == "ною":
                    decl_form["bare"] = "арестованною"
                    decl_form["accented"] = "аресто'ванною"

        if d["bare"] in ["ясный", "точный"]:
            for gender in [RussianGender.M, RussianGender.F, RussianGender.N]:
                (
                    d["ground_truth_decls"][f"inst_{gender}"], 
                    d["ground_truth_decls"][f"prep_{gender}"]
                ) = (
                    d["ground_truth_decls"][f"prep_{gender}"], 
                    d["ground_truth_decls"][f"inst_{gender}"]
                )

        if d["bare"] in delimiter_mapping:
            short_pls = d["ground_truth_decls"]["short_pl"][0]["accented"].split(delimiter_mapping[d["bare"]])
            d["ground_truth_decls"]["short_pl"] = []
            for i, short_pl in enumerate(short_pls):
                d["ground_truth_decls"]["short_pl"].append({
                    "position": str(i+1),
                    "bare": remove_accent_mark(short_pl),
                    "accented": short_pl,
                })
        
        if d["bare"] == "кислый":
            for decl_form in d["ground_truth_decls"]["short_pl"]:
                if decl_form["bare"] == "киcлы":
                    decl_form["bare"] = "кислы"
                    decl_form["accented"] = "кислы'"
        
        # if (
        #     "translations" not in d["meta"]
        #     or (
        #         "translations" in d["meta"]
        #         and len(d["meta"]["translations"]) == 0
        #     )
        # ):
        #     adjectives_to_remove.append(nom_m_id)
        #     print(f"Removing {d['bare']}/{d['accented']} ({nom_m_id}) as it has not translations.")

    for nom_m_id in adjectives_to_remove:
        del adjective_analyses[nom_m_id]

    return adjective_analyses


def apply_declensions(russian_adjective):

    decls = {}
    for decl_type in RUSSIAN_ADJECTIVE_DECLENSION_TYPES:
        decl = eval(f"russian_adjective.{decl_type}")
        decls[decl_type] = decl

    return decls


def make_row(d):
    
    row = dict(
        bare_form=d["bare"],
        accented_form=d["accented"],
        # Meta info.
        suffix=(d["bare"][(
            -3
            if not d["bare"].endswith(RUSSIAN_REFLEXIVE_SUFFIX_CJA)
            else -5
        ):]),
        translations="; ".join(d["meta"].get("translations", "")),
        is_incomparable=eval_boolean(d["meta"]["incomparable"]),
        usage=d["meta"]["usage"],
    )

    # Make tags.

    irreg_decl_tags = []
    accent_chg_tags = []
    multi_vars_tags = []
    
    for decl_type in RUSSIAN_ADJECTIVE_DECLENSION_TYPES:
        
        ground_truth_decl_forms = get_ground_truth_declension_forms(d, decl_type)
        row[decl_type] = "/".join(ground_truth_decl_forms)
        # Remove () if any.
        for i in range(len(ground_truth_decl_forms)):
            if (
                ground_truth_decl_forms[i][0] == "("
                and ground_truth_decl_forms[i][-1] == ")"
            ):
                ground_truth_decl_forms[i] = ground_truth_decl_forms[i][1:-1]

        rule_based_decl_form = get_rule_based_declension_form(d, decl_type)

        irregular_declension_indices = get_irregular_declension_indices(
            ground_truth_decl_forms,
            rule_based_decl_form,
        )
        accent_change_indices = get_accent_change_indices(
            ground_truth_decl_forms,
            rule_based_decl_form,
        )

        # Fix the two endings in acc_{sg|pl}, inst_f.
        if (
            decl_type in ["acc_m", "acc_pl", "inst_f"]
        ):
            print("Fixing two endings in acc_{sg|pl}, inst_f:", d["accented"], rule_based_decl_form)

            rule_based_decl_forms = rule_based_decl_form.split("/")
            for i, ground_truth_decl_form in enumerate(ground_truth_decl_forms):
                if (
                    ground_truth_decl_form in rule_based_decl_forms
                    and i in irregular_declension_indices
                ):
                    irregular_declension_indices.remove(i)

        # Fix по/ей in comparative.
        if (
            decl_type == "comparative"
        ):
            for i, ground_truth_decl_form in enumerate(ground_truth_decl_forms):
                ground_truth_decl_form_ = remove_accent_mark(
                    ground_truth_decl_form,
                    should_normalize_jo=True,
                )
                rule_based_decl_form_ = remove_accent_mark(
                    rule_based_decl_form,
                    should_normalize_jo=True,
                )
                
                if (
                    ground_truth_decl_form_ == rule_based_decl_form_[:-2] + "ей"
                    or ground_truth_decl_form_ == "по" + rule_based_decl_form_
                    or ground_truth_decl_form_ == "по" + rule_based_decl_form_[:-2] + "ей"
                ):
                    print("Fixing по/ей in comparative:", d["accented"], ground_truth_decl_form)
                    irregular_declension_indices.remove(i)

        irregular_declension_indices.sort()
        accent_change_indices.sort()

        mapping = {}   

        if len(irregular_declension_indices) >= 1:
            mapping[irregular_declension_key] = ":".join(list(map(
                str,
                irregular_declension_indices,
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
                (accent_change_key, accent_chg_tags, "a"), 
                (multiple_variants_key, multi_vars_tags, "m")
            ],
            mapping=mapping,
            conjugation_name=decl_type,
        )
        row[f"{decl_type}_tags"] = bits_str + ", ".join(tags)

    for k in [
        irregular_declension_key,
        accent_change_key, 
        multiple_variants_key
    ]:
        row[k] = ",".join(eval(f"{k}_tags"))

    return row


def main(tokens: List[str], adjectives: List[dict], words: List[dict], words_forms: List[dict], translations: List[dict], fp_analyses: str):
    """Analyze adjectives.

    Output file format:

        bare_form, accented_form, suffix, translations, is_incomparable, usage,
        {nom|gen|dat|acc|inst|prep}_{m|f|n|pl}, {nom|gen|dat|acc|inst|prep}_{m|f|n|pl}_tags,
        comparative, superlative,
        short_{m|f|n|pl}, short_{m|f|n|pl}_tags,
        irreg_decl, accent_chg, multi_vars

    Tags of each declension type includes

        1. irregular_declension (irreg_decl)
        2. accent_change (accent_chg)
        3. multiple_variants (multi_vars)

    Steps:

        1. Get all adjective tokens from `tokens`.
        2. Get all nom ms from the adjective tokens.
            I.e., for each adjective token, if it is a nom m, do nothing, else get its nom m.
        3. For each nom m:
            a. Get its bare and accented forms.
            b. Get its meta info (e.g., is_incomparable, etc.).
            c. Get its ground-truth declensions.
            d. Perform declensions according to the Russian adjective declension rules and
                compare the declensions with the ground truth. Mark all inconsistent declensions with
                decl_tags.

    """

    nom_m_ids = get_nom_m_ids(
        tokens=tokens,
        words=words,
        words_forms=words_forms,
    )

    adjective_analyses = get_adjective_analyses(
        nom_m_ids=nom_m_ids,
        words=words,
        adjectives=adjectives,
        words_forms=words_forms,
        translations=translations,
    )
    adjective_analyses = fix_adjective_analyses(
        adjective_analyses
    )

    rows = []
    for _, d in adjective_analyses.items():

        russian_adjective = RussianAdjective(
            accented=d["accented"],
        )
        d["rule_based_decls"] = apply_declensions(russian_adjective)

        row = make_row(d)
        rows.append(row)

        # from pprint import pprint
        # pprint(d)
        # input()

    write_csv(
        fp=fp_analyses,
        l=list(sorted(
            rows,
            key=lambda r: r["bare_form"]
        )),
    )


if __name__ == '__main__':
    tokens = read_tokens(
        fp_words="uploads/words.ru.json",
        fp_articles="uploads/articles.ru.json",
        duolingo_only_articles=True,
    )
    print(f"#tokens: {len(tokens):,}")

    adjectives = read_csv(fp="russian_word_analyses/resources/adjectives.csv")
    words = read_csv(fp="russian_word_analyses/resources/words.csv")  # Adjectives in `words` are infinitives.
    words_forms = read_csv(fp="russian_word_analyses/resources/words_forms.csv")
    translations = read_csv(fp="russian_word_analyses/resources/translations.csv")
    print(
        f"#adjectives: {len(adjectives):,}, "
        f"#words: {len(words):,}, "
        f"#words_forms: {len(words_forms):,}, "
        f"#translations: {len(translations):,}"
    )

    fp_analyses = "adjective_analyses.csv"
    main(
        tokens=tokens,
        adjectives=adjectives,
        words=words,
        words_forms=words_forms,
        translations=translations,
        fp_analyses=fp_analyses,
    )
