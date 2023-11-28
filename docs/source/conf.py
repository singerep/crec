# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import sys
import os
sys.path.insert(0, os.path.abspath('../..'))

project = 'crec'
copyright = '2022-2023 Ethan Singer, Thomson Reuters Special Services LLC'
author = 'Ethan Singer, Spencer Torene, Berk Ekmekci'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.napoleon', 'sphinx.ext.autosectionlabel', 'sphinx.ext.linkcode', "sphinxext.opengraph"]
pygments_style = 'sphinx'

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'sphinx_rtd_theme'
autodoc_member_order = 'bysource'
html_static_path = ['_static']

html_context = {
    "display_github": True, # Integrate GitHub
    'display_version': True,
    "github_user": "singerep", # Username
    "github_repo": "crec", # Repo name
    "github_version": "main", # Version
    "conf_py_path": "/docs/source/", # Path in the checkout to the docs root,
    "html_theme": 'sphinx_rtd_theme'
}

def linkcode_resolve(domain, info):
    if domain != 'py':
        return None

    module = info['module'].replace('.', '/')    
    return f"https://github.com/singerep/crec/blob/main/{module}.py"