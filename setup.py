from setuptools import setup, find_packages
import os

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read() if os.path.exists("README.md") else ""

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="para-auditor",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool for auditing consistency across PARA method tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/para-auditor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "para-auditor=src.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["scripts/applescript/*.scpt"],
    },
)