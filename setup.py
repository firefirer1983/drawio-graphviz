import io
import os
from setuptools import find_packages, setup, find_namespace_packages

def read(*paths, **kwargs):
    content = ""
    with io.open(
        os.path.join(os.path.dirname(__file__), *paths),
        encoding=kwargs.get("encoding", "utf8"),
    ) as open_file:
        content = open_file.read().strip()
    return content

def read_requirements(path):
    if not os.path.exists(path):
        return None
    return [
        line.strip()
        for line in read(path).split("\n")
        if not line.startswith(('"', "#", "-", "git+"))
    ]

setup(
    name="gvdraw",
    version=read("VERSION"),
    description="graphviz to drawio exsions",
    url="https://github.com/firefirer1983/gvdraw/",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="zhang.xuyi",
    packages=find_packages(exclude=[".github", "gvdraw.egg-info"]),  # 找到 src 目录下的所有包
    # package_dir={'': 'gvdraw'},  # 指定包的根目录
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',    
    install_requires=read_requirements("requirements.txt"),
    entry_points={
        "console_scripts": ["json2xml = gvdraw.json2xml:main", "trans2xml = gvdraw.trans2xml:main"],
    },
    extras_require={"test": read_requirements("requirements-test.txt")},
)
