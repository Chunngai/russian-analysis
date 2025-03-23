import csv
import json
import string
from typing import Optional, List, Union


def read_json(fp: str) -> Union[list, dict]:
    with open(fp, "r", encoding="utf-8") as f:
        j = json.load(f)
    return j


def read_csv(fp: str) -> List[dict]:
    with open(fp, "r", encoding="utf-8-sig") as f:
        csv_reader = csv.DictReader(f)
        return list(csv_reader)
    

def write_csv(fp: str, l: List[dict]):
    with open(fp, "w", encoding="utf-8") as f:
        csv_writer = csv.DictWriter(f, fieldnames=list(l[0].keys()))
        csv_writer.writeheader()
        csv_writer.writerows(l)


def read_tokens(
        fp_words: Optional[str] = None,
        fp_articles: Optional[str] = None,
        duolingo_only_articles: bool = False
) -> List[str]:
    """Read tokens from the given word json and article json.

    :param fp_words: E.g., "uploads/words.ru.json"
    :param fp_articles: E.g., "uploads/articles.ru.json"
    :return: Token list.
    """

    tokens = []

    if fp_words is not None:
        for d in read_json(fp=fp_words):
            tokens.extend(d["text"].strip().split())

    if fp_articles is not None:
        for d in read_json(fp=fp_articles):
            
            if (
                duolingo_only_articles 
                and d["topic"].lower() != "duolingo sentences"
            ):
                continue

            for para in d["paras"]:
                tokens.extend(para["text"].strip().split())

    chrs_to_strip = (
        " "
        + string.punctuation
        + string.digits
        + string.ascii_letters
        + "«»–—ー"
    )
    tokens = list(sorted(set(map(
        lambda token: token.lower().strip(chrs_to_strip),
        tokens
    ))))

    return tokens
