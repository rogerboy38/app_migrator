from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="complex_source_app",
    version="2.0.0",
    description="Complex source app for migration testing",
    author="Complex User",
    author_email="complex@example.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
