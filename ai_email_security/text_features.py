import re
import unicodedata

PREPROCESSING_VERSION = "subject-body-v1"


def prepare_text(subject, body):
    text = unicodedata.normalize("NFKC", f"{subject}\n{body}")
    return re.sub(r"\s+", " ", text).strip()


def mail_text(mail):
    return prepare_text(mail["headers"]["Subject"], mail["text"])
