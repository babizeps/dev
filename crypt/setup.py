from setuptools import setup, find_packages

setup(
    name="crypt",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "cryptography>=42.0.0",
        "click>=8.1.0",
        "pyperclip>=1.8.0",
    ],
    entry_points={
        "console_scripts": [
            "crypt=crypt.cli:cli",
        ],
    },
)
