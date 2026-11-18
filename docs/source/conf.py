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
napoleon_include_init_with_doc = True

templates_path = ["_templates"]
exclude_patterns: list[str] = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]
