"""Preserve raw utterances; normalize only for deterministic analysis."""
import re
import unicodedata

def normalize(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).strip()

def corrected(text):
    return re.split(r'아니[,， ]+|정정할게|다시말하면', text)[-1]
