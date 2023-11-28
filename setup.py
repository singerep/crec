from setuptools import setup, find_packages

setup(
    name="crec",
    version="0.0.1",
    description="A python tool built for retrieving, structuring, and enriching the Congressional Record, the official record of the proceedings of the United States Congress. crec wraps the GovInfo API — a product of the U.S. Government Publishing Office — with an intuitive and powerful API of its own.",
    long_description_content_type="text/markdown",
    author="Ethan Singer, Spencer Torene, Berk Ekmekci",
    author_email="singerep@bu.edu, Spencer.Torene@trssllc.com, Berk.Ekmekci@trssllc.com",
    packages=['crec']
)