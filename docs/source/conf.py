# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "dicing"
copyright = "2025, Cewerty"
author = "Cewerty"
from importlib.metadata import version as _version

release = _version("dicing")

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # Для поддержки Google-style docstrings
]

autodoc_default_options = {"members": True, "undoc-members": True, "show-inheritance": True}
autodoc_type_aliases = {"RollStrategy | None": "Optional[RollStrategy]"}
autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_use_ivar = True  # "Attributes" sections as :ivar: so dataclass fields are not documented twice
napoleon_include_init_with_doc = True

templates_path = ["_templates"]
exclude_patterns: list[str] = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]


# -- Docstring style ---------------------------------------------------------
# Docstrings of the project use numpydoc-like underlines under Google-style sections
# ("Returns:" + "-------", or "Attributes" + "----------"). Napoleon would leave the dashes
# in the text and reStructuredText reports "Title underline too short", so they are normalized first.
import re

_SECTIONS = r"Args|Arguments|Attributes|Example|Examples|Note|Notes|Raises|Returns|Warning|Warnings|Yields"
_UNDERLINE = re.compile(r"^\s*-{3,}\s*$")
_HEADER = re.compile(rf"^(\s*)({_SECTIONS}):?\s*$")


def _normalize_sections(app, what, name, obj, options, lines):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN202, ARG001
    """Turn ``Section`` / ``Section:`` followed by a dashed line into a plain Google-style ``Section:``."""
    i = 0
    while i < len(lines):
        match = _HEADER.match(lines[i])
        if match and i + 1 < len(lines) and _UNDERLINE.match(lines[i + 1]):
            lines[i] = f"{match.group(1)}{match.group(2)}:"
            del lines[i + 1]
        i += 1


def setup(app):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN202
    """Register the docstring normalizer before Napoleon (priority 500) processes the lines."""
    app.connect("autodoc-process-docstring", _normalize_sections, priority=100)
