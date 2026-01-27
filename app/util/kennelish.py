# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import logging
from html import escape
from typing import Literal

from pydantic import constr, create_model

logger = logging.getLogger(__name__)


# Known bug: You cannot pre-fill data stored in second-level DynamoDB levels.
# So "parent.child" won't retrieve a value.
class Kennelish:
    """
    Kennelish (a pun off of GitHub://ZenithDevs/Kennel) is a recursive JSON form renderer.
    It renders JSON as an HTML form. Note that this has NO correlation with Sileo's native
    depiction format, and the similarities were accidential.

    """

    def __init__(self):
        super(Kennelish, self).__init__()

    def parse(obj, user_data=None):
        output = ""
        for entry in obj:
            try:
                if entry["input"] == "h1":
                    output += Kennelish.header(entry, user_data)
                elif entry["input"] == "h2":
                    output += Kennelish.header(entry, user_data, "h2")
                elif entry["input"] == "h3":
                    output += Kennelish.header(entry, user_data, "h3")
                elif entry["input"] == "p":
                    output += Kennelish.header(entry, user_data, "p")
                elif entry["input"] == "email":
                    output += Kennelish.text(entry, user_data, "email")
                elif entry["input"] == "nid":
                    output += Kennelish.text(entry, user_data, "nid")
                elif entry["input"] == "text":
                    output += Kennelish.text(entry, user_data)
                elif entry["input"] == "radio":
                    output += Kennelish.radio(entry, user_data)
                elif entry["input"] == "checkbox":
                    output += Kennelish.checkbox(entry, user_data)
                elif entry["input"] == "dropdown":
                    output += Kennelish.dropdown(entry, user_data)
                elif entry["input"] == "slider":
                    output += Kennelish.slider(entry, user_data)
                elif entry["input"] == "signature":
                    output += Kennelish.signature(entry, user_data)
                elif entry["input"] == "navigation":
                    output += Kennelish.navigation(entry)
                else:
                    output += Kennelish.invalid(entry)
            except Exception as e:
                logger.exception(e)
                output += Kennelish.invalid({"input": "Malformed object"})
                continue

        return output

    def label(entry, innerHtml):
        # Labels and captions are admin-controlled, don't escape (may contain HTML links)
        text = f"<h3>{entry.get('label', '')}</h3>"
        text += f"<h4>{entry.get('caption', '')}</h4>"
        return f"<div class='entry'><div>{text}</div><div>{innerHtml}</div></div>"

    def header(entry, user_data=None, tag="h1"):
        # Labels are admin-controlled, don't escape
        output = f"<{tag}>{entry.get('label', '')}</{tag}>"
        output += Kennelish.parse(entry.get("elements", []), user_data)
        return output

    def signature(entry, user_data=None):
        first = escape(user_data.get("first_name", "HackUCF Member #" + str(user_data.get("id"))))
        last = escape(user_data.get("surname", ""))
        key = escape(entry.get("key", ""))
        output = f"<div name='{key}' class='signature'>By submitting this form, you, {first} {last}, agree to the above terms. This form will be time-stamped. By submitting this form, you acknowledge that your submission constitutes a digital signature, which is legally binding and has the same effect as your handwritten signature. This digital signature confirms your consent to the terms and conditions outlined in this document and your agreement to conduct this transaction electronically.</div>"
        return output

    def text(entry, user_data=None, inp_type="text"):
        # Pre-filling of data from database (+ special rule for email discovery)
        if entry.get("prefill", True):
            key = entry.get("key", "")
            if key == "email":
                if user_data.get("email"):
                    prefill = user_data.get("email")
                else:
                    prefill = user_data.get("discord").get("email")
            else:
                prefill = user_data.get(key, "")

            if prefill is None:
                prefill = ""
        else:
            prefill = ""

        regex_pattern = " "
        if inp_type == "email" and entry.get("domain", False):
            regex_pattern = ' pattern="([A-Za-z0-9.-_+]+)@' + escape(entry.get("domain")) + '"'
        elif inp_type == "email":
            regex_pattern = ' pattern="([A-Za-z0-9.-_+]+)@[A-Za-z0-9-]+(.[A-Za-z-]{2,})"'
        elif inp_type == "nid":
            regex_pattern = ' pattern="^([a-z]{2}[0-9]{6})$"'

        # Escape: prefill (user data), key (attribute safety)
        # Don't escape: label/placeholder (admin config, but goes in attribute so escape for safety)
        output = f"<input class='kennelish_input'{' required' if entry.get('required') else ' '}{regex_pattern} name='{escape(entry.get('key', ''))}' type='{'text' if inp_type == 'nid' else inp_type}' value='{escape(str(prefill))}' placeholder='{escape(entry.get('label', ''))}' />"
        return Kennelish.label(entry, output)

    def radio(entry, user_data=None):
        # Pre-filling of data from database
        if entry.get("prefill", True):
            prefill = user_data.get(entry.get("key", ""), "")
            if str(prefill) == "True":
                prefill = "Yes"
            elif str(prefill) == "False":
                prefill = "No"
        else:
            prefill = ""

        # Escape keys in attributes, but options are admin config (don't escape in label text)
        key = escape(entry.get("key", ""))
        key_id = entry.get("key", "").replace(".", "_").replace(" ", "_")
        output = f"<fieldset name='{key}'{' required' if entry.get('required') else ' '} class='kennelish_input radio'>"
        for option in entry["options"]:
            selected = "" if option != prefill else "checked"
            option_escaped = escape(str(option))  # Escape for attribute safety
            option_id = str(option).replace(".", "_").replace(" ", "_")
            # Use escaped option in value attribute, but unescaped in label text (admin config)
            output += f"<div><input type='radio' {selected} name='{key}' id='radio_{key_id}_{option_id}' value='{option_escaped}'><label for='radio_{key_id}_{option_id}'>{option}</label></div>"
        output += "</fieldset>"
        return Kennelish.label(entry, output)

    def checkbox(entry, user_data=None):
        # Checkboxes do not support pre-filling!

        # Escape keys in attributes, but options are admin config (don't escape in label text)
        key = escape(entry.get("key", ""))
        key_id = entry.get("key", "").replace(".", "_").replace(" ", "_")
        output = f"<fieldset name='{key}'{' required' if entry.get('required') else ' '} class='kennelish_input checkbox'>"
        for option in entry.get("options"):
            option_escaped = escape(str(option))  # Escape for attribute safety
            option_id = str(option).replace(".", "_").replace(" ", "_")
            # Use escaped option in value attribute, but unescaped in label text (admin config)
            output += f"<div><input type='checkbox' name='{key}' id='checkbox_{key_id}_{option_id}' value='{option_escaped}'><label for='checkbox_{key_id}_{option_id}'>{option}</label></div>"

        # Other
        output += f"<div><input type='checkbox' name='{key}' id='checkbox_{key_id}_OTHER' value='_other'><label for='checkbox_{key_id}_OTHER'>Other</label></div>"
        output += f"<input id='{key_id}' class='other_checkbox' type='text' placeholder='{escape(entry.get('label', 'Other'))}...'>"
        output += "</fieldset>"
        return Kennelish.label(entry, output)

    def dropdown(entry, user_data=None):
        # Pre-filling of data from database
        if entry.get("prefill", True):
            prefill = user_data.get(entry.get("key", ""), "_default")
            if prefill == "":
                prefill = "_default"
        else:
            prefill = "_default"

        # Escape keys in attributes, but options are admin config (don't escape in option text)
        key = escape(entry.get("key", ""))
        key_id = entry.get("key", "").replace(".", "_").replace(" ", "_")
        output = f"<select class='kennelish_input'{' required' if entry.get('required') else ' '} name='{key}'><option disabled {'selected ' if prefill == '_default' else ''}value='_default'>Select...</option>"
        for option in entry.get("options"):
            option_escaped = escape(str(option))  # Escape for attribute safety
            # Use escaped option in value attribute, but unescaped in option text (admin config)
            output += f"<option {'selected ' if prefill == option else ''}value='{option_escaped}'>{option}</option>"

        if entry.get("other"):
            output += f"<option value='_other'>Other</option></select><input id='{key_id}' class='other_dropdown' type='text' placeholder='{escape(entry.get('label', 'Other'))}...'>"
        else:
            output += "</select>"
        return Kennelish.label(entry, output)

    def slider(entry, user_data=None):
        # This is pretty much radio, but modified.

        # Pre-filling of data from database
        if entry.get("prefill", True):
            prefill = user_data.get(entry.get("key", ""), "")
        else:
            prefill = ""

        # Labels are admin config, but in content so don't escape
        novice_label = entry.get("novice_label", "Novice")
        expert_label = entry.get("expert_label", "Expert")

        # Escape key in attributes
        key = escape(entry.get("key", ""))
        key_id = entry.get("key", "").replace(".", "_").replace(" ", "_")
        output = f"<span class='caption'>{novice_label}</span><span class='right caption'>{expert_label}</span><br>"
        output += f"<fieldset name='{key}'{' required' if entry.get('required') else ' '} class='kennelish_input radio gridded'>"
        for option in range(1, 6):
            selected = "" if option != prefill else "checked"
            output += f"<div><input type='radio' {selected} name='{key}' id='radio_{key_id}_{option}' value='{option}'><label for='radio_{key_id}_{option}'>{option}</label></div>"
        output += "</fieldset>"
        return Kennelish.label(entry, output)

    def navigation(entry):
        if entry.get("prev"):
            # back = f"<a class='btn wide grey' href='{entry.get('prev', '#')}'>{entry.get('prev_label', 'Back')}</a>"
            # Escape URLs in attributes for safety, but labels are admin config (don't escape)
            prev_url = escape(entry.get("prev", "#")).replace('"', "&quot;")
            prev_label = entry.get("prev_label", "Back")
            back = f"<button type='button' class='btn wide grey' onclick='submit_and_nav(\"{prev_url}\")'>{prev_label}</button>"
        else:
            back = ""
        next_url = escape(entry.get("next", "#")).replace('"', "&quot;")
        next_label = entry.get("next_label", "Next")
        forward = f"<button type='button' class='btn wide' onclick='submit_and_nav(\"{next_url}\")'>{next_label}</button>"
        return f"<div class='entry'><div>{back}</div><div>{forward}</div></div>"

    def invalid(entry):
        return f"<h3 class='invalid'>Invalid Input: {escape(str(entry.get('input', 'Unknown')))}</h3>"


class Transformer:
    """
    Transforms a Kennelish file into a Pydantic model for validation.

    Some terminology to help out:
    - Form: Think of this as the JSON you would send the API.
    - Kennelish: The JSON file that renders the page.
    - Pydantic: A library for strict typing. See: https://pydantic-docs.helpmanual.io/
    """

    def __init__(self):
        super(Transformer, self).__init__()

    def kwargs_to_str(kwargs):
        for k, v in kwargs.items():
            kwargs[k] = str(v)

        return kwargs

    def kennelish_to_form(json):
        obj = {}

        if json is None:
            return {}

        for el in json:
            element_type = el.get("input")

            # For if we have an element that contains other elements.
            if element_type == "h1" or element_type == "h2":
                obj = {**obj, **Transformer.kennelish_to_form(el.get("elements"))}

            # For when a choice is REQUIRED.
            elif element_type == "radio" or (element_type == "dropdown" and not el.get("other", True)):
                obj[el.get("key")] = (Literal[tuple(el.get("options"))], None)

            # For emails (specified domain)
            elif element_type == "email" and el.get("domain", False):
                domain_regex = rf"^[A-Za-z0-9._%+-]+@{el.get('domain').lower()}$"
                regex_constr = constr(pattern=domain_regex)
                obj[el.get("key")] = (regex_constr, None)

            # For emails (any domain)
            elif element_type == "email":
                regex_constr = constr(pattern=r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
                obj[el.get("key")] = (regex_constr, None)

            # For NIDs
            elif element_type == "nid":
                regex_constr = constr(pattern="(^([a-z]{2}[0-9]{6})$)")
                obj[el.get("key")] = (regex_constr, None)

            # For numbers
            elif element_type == "slider":
                obj[el.get("key")] = (int, None)

            # Timestamps
            elif element_type == "signature":
                obj[el.get("key")] = (int, None)

            # For arbitrary strings.
            elif el.get("key") is not None:
                obj[el.get("key")] = (str, None)

        return obj

    def form_to_pydantic(json):
        model = create_model("KennelishGeneratedModel", **json)
        return model

    def kennelish_to_pydantic(json):
        form = Transformer.kennelish_to_form(json)
        return Transformer.form_to_pydantic(form)
