from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = f.read().strip().split('\n')

setup(
    name='app_migrator',
    version='1.0.0',
    description='Frappe App Migration Toolkit',
    author='Frappe Community',
    author_email='fcrm@amb-wellness.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
