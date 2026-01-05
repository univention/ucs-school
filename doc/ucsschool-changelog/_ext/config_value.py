# SPDX-FileCopyrightText: 2025-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from docutils import nodes
from docutils.parsers.rst import roles


def config_value_no_spelling(name, rawtext, text, lineno, inliner, options={}, content=[]):
    value = inliner.document.settings.env.app.config[text]
    node = nodes.inline(text=value)
    return [node], []


def setup(app):
    roles.register_local_role("config-value-no-spelling", config_value_no_spelling)
    return {"version": "1.0.0"}
