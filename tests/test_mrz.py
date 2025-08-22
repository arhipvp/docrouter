import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from file_utils.mrz import parse_mrz


def test_parse_mrz_extracts_fields():
    text = (
        "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\n"
        "L898902C<3UTO7408122F1204159ZE184226B<<<<<<<<<10"
    )
    result = parse_mrz(text)
    assert result["passport_number"] == "L898902C3"
    assert result["person"] == "ANNA MARIA ERIKSSON"
    assert result["date_of_birth"] == "1974-08-12"
    assert result["expiration_date"] == "2012-04-15"
