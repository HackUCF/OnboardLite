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
            with open(safe_path, "r") as form_file:
                return json.load(form_file)
        except FileNotFoundError:
            raise FileNotFoundError


# Correct answers for multiple-choice / quiz-style forms, keyed by form num
# then by field key. Deliberately kept out of app/forms/*.json: GET /api/form/{num}
# returns that file verbatim to anyone unauthenticated (form files aren't
# considered sensitive), so embedding answers there would hand out the quiz key.
# Each answer must match one of the radio's options exactly.
FORM_CORRECT_ANSWERS: dict[str, dict[str, str]] = {
    "admin_compliance": {
        "admin_compliance_reporter_ack": "Route it through whoever's handling PR and don't share member info myself — being an exec is not a personal press office license.",
        "admin_compliance_government_ack": "Politely decline to answer, get their contact info, and immediately loop in the rest of the exec board",
        "admin_compliance_first_amendment_ack": "Forcing disclosure violated members' First Amendment right to freedom of association.",
        "admin_compliance_sponsor_ack": "Offer to build a resume pool of members who've opted in, or offer to forward the job listing to our members",
        "admin_compliance_peer_ack": "Share only what's actually needed for a purpose tied to the requester's own role; for anyone else (including officers asking outside their lane), redirect them to the member directly or loop in the board.",
    }
}


def iter_form_elements(kennelish_data):
    """Yield every element in a Kennelish form, descending into h1/h2 sections."""
    for el in kennelish_data or []:
        yield el
        if el.get("elements"):
            yield from iter_form_elements(el.get("elements"))


def wrong_quiz_answers(num: str, kennelish_data, submitted: dict) -> list[str]:
    """
    Return the headings of the quiz questions in form `num` that `submitted`
    got wrong (empty if all correct or the form isn't graded). A question's
    heading is the nearest h3 above its radio, falling back to its key.
    """
    answers = FORM_CORRECT_ANSWERS.get(num, {})
    wrong = []
    heading = None
    for el in iter_form_elements(kennelish_data):
        if el.get("input") == "h3":
            heading = el.get("label")
        key = el.get("key")
        if key in answers and submitted.get(key) != answers[key]:
            wrong.append(heading or key)
    return wrong


def prefill_quiz_answers(num: str, user_data: dict) -> dict:
    """
    Graded answers are stored as True once passed; map them back to the
    correct option text so the form re-renders with them selected.
    """
    for key, correct_value in FORM_CORRECT_ANSWERS.get(num, {}).items():
        if user_data.get(key) is True:
            user_data[key] = correct_value
    return user_data


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
