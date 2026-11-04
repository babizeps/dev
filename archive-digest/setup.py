from setuptools import setup, find_packages

setup(
    name="archive-digest",
    version="0.1.0",
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "anthropic>=2.4.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "click>=8.1.0",
    ],
    entry_points={
        "console_scripts": [
            "archive-digest=archive_digest.cli:cli",
        ],
    },
)
