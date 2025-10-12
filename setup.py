from setuptools import setup, find_packages

# get version from __version__ variable in app_migrator/__init__.py
from app_migrator import __version__ as version

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="app_migrator",
    version=version,
    description="Ultimate Frappe App Migration System",
    author="Frappe Community",
    author_email="fcrm@amb-wellness.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
