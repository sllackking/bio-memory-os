from setuptools import setup, find_packages

setup(
    name="bio-memory-os",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "gitpython>=3.1.0",  # Git 操作
    ],
    extras_require={
        "local": ["sentence-transformers>=2.0.0", "tree-sitter>=0.20.0"],
        "code": ["tree-sitter-python", "networkx>=2.6"],
    },
    entry_points={
        'console_scripts': [
            'bio-memory=bio_memory_os.cli:main',
        ],
    },
    python_requires='>=3.8',
)
