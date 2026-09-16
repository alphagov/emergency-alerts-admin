from dataclasses import fields, is_dataclass

import pytest

from app.utils.labels import LABELS, Labels


def test_labels_immutability():
    """Ensure the root and child dataclasses remain frozen/read-only."""
    with pytest.raises(Exception):
        LABELS.broadcast = None

    with pytest.raises(Exception):
        LABELS.broadcast.submit_for_approval_confirmation_button = "Mutated"

    with pytest.raises(Exception):
        LABELS.service = None

    with pytest.raises(Exception):
        LABELS.service.training_service_status = "Mutated"


def test_all_nested_attributes_are_non_empty_strings():
    """Recursively verify all leaf fields are non-empty strings.
    Automatically tests all existing and future nested dataclass fields.
    """

    def check_dataclass_fields(instance):
        for field in fields(instance):
            val = getattr(instance, field.name)
            if is_dataclass(val):
                check_dataclass_fields(val)
            else:
                assert isinstance(val, str), f"Field '{field.name}' in {type(instance).__name__} is not a string"
                assert len(val.strip()) > 0, f"Field '{field.name}' in {type(instance).__name__} is empty"

    check_dataclass_fields(LABELS)


def test_all_nested_dataclasses_are_frozen():
    """Ensure future developers don't forget `frozen=True` on new child dataclasses."""

    def check_frozen(cls):
        assert cls.__dataclass_params__.frozen, f"{cls.__name__} must be declared with frozen=True"
        for field in fields(cls):
            if is_dataclass(field.type):
                check_frozen(field.type)

    check_frozen(Labels)


def test_labels_singleton_instantiation():
    """Verify default instantiation of the root Labels class matches the exported constant."""
    assert LABELS == Labels()
