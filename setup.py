#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="lxml-readability",
    version="0.06dev",
    author="Yuri Baburov, Jaran Charumilind",
    author_email="lorax@jcharum.fastmail.net",
    description="python port of arc90's readability bookmarklet",
    long_description=open("README").read(),
    license="Apache License 2.0",
    url="http://github.com/buriy/python-readability",
    packages=find_packages(),
    install_requires=[
        "chardet"
        ],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        ],
)
