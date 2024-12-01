from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="orbitarium",
    version="1.0.0",
    author="Fabian Köll",
    description="A library to approximate positions of planets and moons in our Solar System.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/koell/orbitarium",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
