from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gamefriend",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool for downloading GameFAQs guides as markdown files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/gamefriend",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "click>=8.1.0",
        "rich>=13.7.0",
        "markdown>=3.5.0",
    ],
    entry_points={
        "console_scripts": [
            "gamefriend=gamefriend.cli:cli",
        ],
    },
)
