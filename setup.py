#!/usr/bin/env python

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rust_magic",
    version="0.1.0",
    author='Lev Maximov',
    author_email='lev.maximov@gmail.com',
    url='https://github.com/axil/rust-magic',
    description="Lightweight Rust integration in Jupyter notebook",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=['rust_magic'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    zip_safe=False,
)

