from setuptools import setup, find_packages

setup(
    name="bio-memory-os",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "gitpython>=3.1.0",
    ],
    extras_require={
        "local": ["sentence-transformers>=2.0.0", "tree-sitter>=0.20.0"],
        "code": ["tree-sitter-python", "networkx>=2.6"],
    },
    python_requires='>=3.8',
    description="仿生记忆操作系统 - 防128k溢出，十年可验证",
    author="OpenClaw User",
    license="MIT",
)
