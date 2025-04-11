ACCENT_MARK = "'"

RUSSIAN_VOWELS = "аеёиоуыэюя"
RUSSIAN_CONSONANTS = "бвгджзйклмнпрстфхцчшщ"

RUSSIAN_REFLEXIVE_SUFFIX_CJA = "ся"

irregular_declension_key = "irreg_decl"
Irregular_declension_key = "Irreg_decl"
accent_change_key = "accent_chg"
multiple_variants_key = "multi_vars"


def get_accent_pos(word):
    if ACCENT_MARK not in word:
        return None
    return word.index(ACCENT_MARK) - 1


def get_pos_of_last_vowel(word):
    word = remove_accent_mark(word)
    for i in range(len(word) - 1, -1, -1):
        if word[i] in RUSSIAN_VOWELS:
            return i
    return None


def remove_accent_mark(word):
    word = word.replace(
        ACCENT_MARK,
        ""
    )
    # if should_normalize_jo:
    #     word = word.replace(
    #         "ё",
    #         "е",
    #     )
    return word


def insert_accent_mark(word, accent_pos):
    if accent_pos is None:
        return word
    return word[:accent_pos + 1] + ACCENT_MARK + word[accent_pos + 1:]


def supplement_accent_mark(word):
    
    if ACCENT_MARK in word:
        return word
    
    if "ё" in word:
        vowel_pos = word.index("ё")
        return word[:vowel_pos + 1] + ACCENT_MARK + word[vowel_pos + 1:]
    
    vowel_poss = []
    for i, c in enumerate(list(word.lower())):
        if c in RUSSIAN_VOWELS:
            vowel_poss.append(i)

    if len(vowel_poss) == 1:
        vowel_pos = vowel_poss[0]
        return word[:vowel_pos + 1] + ACCENT_MARK + word[vowel_pos + 1:]
    return word


def eval_boolean(val):
    if val.isdigit():
        return bool(int(val))
    else:
        return None
    

def list_enum_values(enum_obj):
    # https://stackoverflow.com/questions/29503339/how-to-get-all-values-from-python-enum-class
    return [
        e.value
        for e in enum_obj
    ]


def has_single_vowel(word):
    vowel_count = 0
    for char in word:
        if char in RUSSIAN_VOWELS:
            vowel_count += 1
        if vowel_count >= 2:
            return False
        
    return vowel_count == 1


def get_ground_truth_declension_forms(d, declension_type):
    return list(map(
        lambda d: d.get(
            "accented",
            ""
        ),
        d.get(  # No declensions for some word. E.g., кофе. 
            "ground_truth_decls",
            {},
        ).get(  # Declensions of some words may not be complete. E.g., sg_only and pl_only words.
            declension_type, 
            [],
        )  
    ))

def get_rule_based_declension_form(d, declension_type):
    return d["rule_based_decls"][declension_type]

def is_irregular_form(ground_truth, rule_based):
    return (
        remove_accent_mark(ground_truth) 
        != remove_accent_mark(rule_based)
    )

def is_accent_changed(ground_truth, rule_based):
    return (
        get_accent_pos(ground_truth)
        != get_accent_pos(rule_based)
    )


def get_irregular_declension_indices(ground_truth_decl_forms, rule_based_decl_form,):

    indices = []
    for i, ground_truth_decl_form in enumerate(ground_truth_decl_forms):

        if is_irregular_form(
            ground_truth_decl_form, 
            rule_based_decl_form
        ):
            indices.append(i)

    return indices


def get_accent_change_indices(ground_truth_decl_forms, rule_based_decl_form,):

    indices = []
    for i, ground_truth_decl_form in enumerate(ground_truth_decl_forms):

        if is_accent_changed(
            ground_truth_decl_form, 
            rule_based_decl_form
        ):
            indices.append(i)

    return indices


def get_bits_str_and_tags(wrapped, mapping, conjugation_name,):

    bits = ["_"] * len(wrapped)
    tags = []
    
    for index, (key, l, bit) in enumerate(wrapped):
        if key not in mapping:
            continue

        if key != multiple_variants_key:
            tag = mapping[key]
            tags.append(f"{key}:{tag}")
            l.append(f"{conjugation_name}:{tag}")
        else:
            l.append(conjugation_name)

        bits[index] = bit

    bits_str = ''.join(bits)
    if bits_str != "_" * len(bits):
        bits_str = f"#{bits_str}, "
    else:
        bits_str = ""

    return (
        bits_str,
        tags,
    )


if __name__ == '__main__':
    accented = "ше'стого"
    bare = "шестого"
    print(
        accented,
        get_accent_pos(accented),
        insert_accent_mark(bare, get_accent_pos(accented)),
        accented == insert_accent_mark(bare, get_accent_pos(accented))
    )
