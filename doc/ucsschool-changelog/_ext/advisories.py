import datetime
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from babel.dates import format_date
from docutils import nodes
from sphinx.util.docutils import SphinxDirective


class AdvisoriesDirective(SphinxDirective):
    """A directive to create changelog entries from advisories."""

    required_arguments = 1

    def collect_advisories(self, directory) -> dict[datetime.datetime, list[dict[str, Any]]]:
        advisories = defaultdict(list)
        todays_date = datetime.datetime.now()
        todays_date = datetime.datetime(
            year=todays_date.year, month=todays_date.month, day=todays_date.day
        )
        for file in (directory / "staging").iterdir():
            if file.is_file() and not file.name == "0template.yaml":
                advisories[todays_date].append(yaml.safe_load(file.open()))
        release = self.state.document.settings.env.app.config.release
        for file in (directory / "published").iterdir():
            if file.is_file() and not file.name == "0template.yaml":
                name_parts = file.name.split("-", 3)
                data = yaml.safe_load(file.open())
                if data["released"].strip() != release:
                    continue
                advisories[
                    datetime.datetime(
                        year=int(name_parts[0]), month=int(name_parts[1]), day=int(name_parts[2])
                    )
                ].append(data)
        return advisories

    def add_title(self, date_obj, section, lang: str):
        if lang == "de":
            title_node = nodes.title(text=f"Veröffentlicht am {format_date(date_obj, locale='de_DE')}")
        else:
            title_node = nodes.title(text=f"Released on {format_date(date_obj, locale='en_US')}")
        section += title_node

    def add_changelog_entry(self, advisory: dict[str, Any], section: nodes.section, lang: str):
        generated = nodes.container()
        if lang == "de":
            text = f"Quellpaket *{advisory['src']}* in Version ``{advisory['fix']}``:"
        else:
            text = f"Source package *{advisory['src']}* in version ``{advisory['fix']}``:"
        self.state.nested_parse(nodes.paragraph(text=text), 0, generated)
        section += generated
        list_node = nodes.bullet_list()
        for bug, entries in advisory["bugs"].items():
            if not isinstance(entries, list):
                entries = [entries]
            for entry in entries:
                content = nodes.list_item()
                entry_raw = entry[lang].strip()
                entry_text = f"{entry_raw[:-1] if entry_raw.endswith('.') else entry_raw}" + (
                    "." if bug == "notes" else f" (:uv:bug:`{bug}`)."
                )
                self.state.nested_parse(
                    nodes.paragraph(text=entry_text),
                    0,
                    content,
                )
                list_node += content
        section += list_node

    def run(self) -> list[nodes.Node]:
        directory = Path(self.arguments[0]).resolve()
        language = self.state.document.settings.language_code
        sections = []
        advisories = self.collect_advisories(directory)
        for date_obj, advisory_list in sorted(advisories.items(), reverse=True):
            section_node = nodes.section()
            self.add_title(date_obj, section_node, language)
            for advisory in sorted(advisory_list, key=lambda item: item["src"]):
                self.add_changelog_entry(advisory, section_node, language)
            section_node["ids"].append(f"changelog-ucsschool-{date_obj.strftime('%Y-%m-%d')}")
            section_node["translatable"] = False
            sections.append(section_node)
        return sections


def setup(app):
    app.add_directive("uv-advisories", AdvisoriesDirective)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
