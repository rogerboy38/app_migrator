from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in app_migrator/__init__.py
from app_migrator import __version__ as version

setup(
    name="app_migrator",
    version="5.1.0",
    description="Frappe App Migration Toolkit v5.0.2",
    author="Frappe Community",
    author_email="fcrm@amb-wellness.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
