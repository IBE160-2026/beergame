import json

import pytest

from app.engine import RuleBasedParams
from app.platform import parameter_sets
from app.platform.parameter_sets import UnknownParameterSetError, read_parameter_set


def test_reads_the_shipped_rule_based_set():
    data = json.loads(read_parameter_set("rule_based", "placeholder-unverified"))
    assert data["id"] == "placeholder-unverified"
    assert data["verified"] is False


def test_reads_a_set_from_another_root(tmp_path):
    (tmp_path / "rule_based").mkdir()
    (tmp_path / "rule_based" / "new-set.json").write_text('{"id": "new-set"}', encoding="utf-8")
    assert json.loads(read_parameter_set("rule_based", "new-set", root=tmp_path)) == {
        "id": "new-set"
    }


@pytest.mark.parametrize(
    ("kind", "set_id"),
    [
        ("rule_based", "nope"),
        ("rule_based", "../rule_based/placeholder-unverified"),
        ("rule_based", "Placeholder-unverified"),
        ("rule_based", ""),
        ("rule_based", "my_set"),
        ("../app", "placeholder-unverified"),
        ("nope", "placeholder-unverified"),
    ],
)
def test_unknown_or_unsafe_sets_raise(kind, set_id):
    with pytest.raises(UnknownParameterSetError):
        read_parameter_set(kind, set_id)


def test_set_ids_follow_the_same_pattern_as_the_parameter_model():
    model_pattern = RuleBasedParams.model_fields["id"].metadata[0].pattern
    assert model_pattern == f"^{parameter_sets._SET_ID.pattern}$"
