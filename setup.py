#!/usr/bin/python

from setuptools import setup, find_packages

setup(
    name="reddit_robin",
    description="April Fools 2016",
    version="0.0",
    packages=find_packages(),
    install_requires=[
        "r2",
    ],
    entry_points={
        "r2.plugin": [
            "robin = reddit_robin:Robin",
        ],
    },
    zip_safe=False,
)
