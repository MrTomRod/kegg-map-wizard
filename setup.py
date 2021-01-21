# https://packaging.python.org/tutorials/packaging-projects/
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="kegg-map-wizard-mrtomrod", # Replace with your own username
    version="0.0.1",
    author='Thomas Roder',
    author_email='roder.thomas@gmail.com',
    description="Exposes KEGG pathways as Python objects, creates SVGs for processing in modern browsers, includes simple JS library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MrTomRod/kegg_map_wizard",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)