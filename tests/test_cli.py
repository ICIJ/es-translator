import click
import pytest

from es_translator.cli import validate_max_content_length


def test_validate_max_content_length():
    assert 18 == validate_max_content_length(None, None, '18')
    assert 18 * 1024 == validate_max_content_length(None, None, '18K')
    assert 18 * 1024 ** 2 == validate_max_content_length(None, None, '18M')
    assert 18 * 1024 ** 3 == validate_max_content_length(None, None, '18G')


def test_validate_max_content_length_bad_syntax():
    with pytest.raises(click.BadParameter) as e_info:
        validate_max_content_length(None, None, '123R')