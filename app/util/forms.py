# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import json
import logging
import os
from pathlib import Path
from typing import DefaultDict

logger = logging.getLogger(__name__)


def resolve_within(user_path: str, allowed_dir: str) -> Path | None:
    """Resolve user_path once and return it only if it's inside allowed_dir."""
    resolved_path = Path(user_path).resolve()
    resolved_dir = Path(allowed_dir).resolve()
    try:
        resolved_path.relative_to(resolved_dir)
        return resolved_path
    except ValueError:
        return None


class Forms:
    @staticmethod
    def get_form_body(file="1"):
        candidate = os.path.join(os.getcwd(), "app/forms", f"{Path(file).name}.json")
        safe_path = resolve_within(candidate, "app/forms")
        if safe_path is None:
            logger.error("attempted to access unauthorized paths")
            raise PermissionError("Access to the specified file is not allowed")
        try:
            return json.load(open(safe_path, "r"))
        except FileNotFoundError:
            raise FileNotFoundError


def fuzzy_parse_value(value):
    # Convert common boolean-like values
    if isinstance(value, str):
        value_test = value.lower()
        if value_test in {"yes", "true", "1", "Yes"}:
            return True
        if value_test in {"no", "false", "0", "No"}:
            return False
        if "i promise not" in value_test:
            return True
        if "i have read the terms and agree to them" in value_test:
            return True
        if "i agree to these terms" in value_test:
            return True

    # Convert other types as needed

    return value


def apply_fuzzy_parsing(data: dict):
    """
    Converts form data from fuzzy boolean values like, yes, no, 'i promise not' into booleans
    """
    parsed_data = {k: fuzzy_parse_value(v) for k, v in data.items()}
    return parsed_data


def transform_dict(d):
    """
    Turns the nested Models in the format nested_model.key1: "1" into nested_model: {key1: "1", key2: "2" }
    """
    if not any("." in key for key in d):
        return d
    nested_dict = DefaultDict(dict)
    for key, value in d.items():
        parent, child = key.split(".")
        nested_dict[parent][child] = value
    return nested_dict
