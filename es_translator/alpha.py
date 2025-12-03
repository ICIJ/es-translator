from pycountry import languages


class InvalidLanguageCode(ValueError):
    """Exception raised when an invalid language code is provided."""

    def __init__(self, code: str) -> None:
        super().__init__(f"Invalid language code: '{code}'")
        self.code = code


def to_alpha_2(code: str) -> str:
    """Convert a language code to ISO 639-1 (2-letter) format.

    Args:
        code: Language code in either 2-letter or 3-letter format.

    Returns:
        The 2-letter language code.

    Raises:
        InvalidLanguageCode: If the language code is not found.
    """
    if len(code) == 3:
        lang = languages.get(alpha_3=code)
        if lang is None:
            raise InvalidLanguageCode(code)
        return lang.alpha_2
    return code


def to_alpha_3(code: str) -> str:
    """Convert a language code to ISO 639-3 (3-letter) format.

    Args:
        code: Language code in either 2-letter or 3-letter format.

    Returns:
        The 3-letter language code.

    Raises:
        InvalidLanguageCode: If the language code is not found.
    """
    if len(code) == 2:
        lang = languages.get(alpha_2=code)
        if lang is None:
            raise InvalidLanguageCode(code)
        return lang.alpha_3
    return code


def to_name(alpha_2: str) -> str:
    """Get the full language name from a 2-letter code.

    Args:
        alpha_2: ISO 639-1 (2-letter) language code.

    Returns:
        The full language name.

    Raises:
        InvalidLanguageCode: If the language code is not found.
    """
    lang = languages.get(alpha_2=alpha_2)
    if lang is None:
        raise InvalidLanguageCode(alpha_2)
    return lang.name


def to_alpha_3_pair(pair: str) -> str:
    """Convert a language pair to ISO 639-3 format.

    Args:
        pair: Language pair in format 'source-target'.

    Returns:
        Language pair with both codes in 3-letter format.
    """
    source, target = pair.split('-')
    return f'{to_alpha_3(source)}-{to_alpha_3(target)}'
