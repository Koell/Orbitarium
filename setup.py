from setuptools import setup, find_packages

setup(
    name="orbitalis",
    version="0.1.0",
    author="Your Name",
    description="A library to approximate positions of planets and moons in the Solar System.",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    url="https://github.com/koell/orbitalis",
    packages=find_packages(),
    license="GPLv3",
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
