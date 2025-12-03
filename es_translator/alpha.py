from pycountry import languages


def to_alpha_2(code: str) -> str:
    """Convert a language code to ISO 639-1 (2-letter) format.

    Args:
        code: Language code in either 2-letter or 3-letter format.

    Returns:
        The 2-letter language code.
    """
    if len(code) == 3:
        return languages.get(alpha_3=code).alpha_2
    return code


def to_alpha_3(code: str) -> str:
    """Convert a language code to ISO 639-3 (3-letter) format.

    Args:
        code: Language code in either 2-letter or 3-letter format.

    Returns:
        The 3-letter language code.
    """
    if len(code) == 2:
        return languages.get(alpha_2=code).alpha_3
    return code


def to_name(alpha_2: str) -> str:
    """Get the full language name from a 2-letter code.

    Args:
        alpha_2: ISO 639-1 (2-letter) language code.

    Returns:
        The full language name.
    """
    return languages.get(alpha_2=alpha_2).name


def to_alpha_3_pair(pair: str) -> str:
    """Convert a language pair to ISO 639-3 format.

    Args:
        pair: Language pair in format 'source-target'.

    Returns:
        Language pair with both codes in 3-letter format.
    """
    source, target = pair.split('-')
    return f'{to_alpha_3(source)}-{to_alpha_3(target)}'
