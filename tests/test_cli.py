import click
import pytest

from es_translator.cli import validate_max_content_length


def test_validate_max_content_length():
    assert validate_max_content_length(None, None, '18') == 18
    assert validate_max_content_length(None, None, '18K') == 18 * 1024
    assert validate_max_content_length(None, None, '18M') == 18 * 1024 ** 2
    assert validate_max_content_length(None, None, '18G') == 18 * 1024 ** 3


def test_validate_max_content_length_bad_syntax():
    with pytest.raises(click.BadParameter):
        validate_max_content_length(None, None, '123R')
