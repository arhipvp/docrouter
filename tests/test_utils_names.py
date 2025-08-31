from utils.names import normalize_person_name


def test_normalizes_commas_and_order():
    assert normalize_person_name("Иван Иванов") == "Иванов Иван"
    assert normalize_person_name("иванов, иван, иванович") == "Иванов Иван Иванович"


def test_removes_duplicates():
    raw = "Иванов Иван Иванович, Иванов Иван Иванович"
    assert normalize_person_name(raw) == "Иванов Иван Иванович"
