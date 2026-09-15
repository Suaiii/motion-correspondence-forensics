"""Normalize only observed generator prefixes; tokens remain unverified ancestry candidates."""
import re


def generator_token(name):
    return re.sub(r'^(ms|vc|vc2|videocrafter2)[-_]', '', name, flags=re.I).rsplit('.',1)[0]
