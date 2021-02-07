
import os
from setuptools import setup, find_namespace_packages


with open("README.md", "r") as fh:
    long_description = fh.read()

current_version = '0.9.0.7'

with open("src/alphazeta/warden/static/config/version.txt", "w") as text_file:
    print(f"{current_version}", file=text_file)


reqs = [
    'Flask-Login',
    'flask_apscheduler',
    'flask_mail',
    'libusb1',
    'pandas',
    'numpy',
    'PySocks',
    'requests',
    'urllib3',
    'simplejson',
    'jsonify'
]

setup(
    name="alphazeta.warden",
    version=current_version,
    author="Alpha Zeta",
    author_email="alphaazeta@protonmail.com",
    description="Private Portfolio Tool - Specter Server Edition",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pxsocs/specter_warden",
    include_package_data=True,
    package_dir={"": "src"},
    install_requires=reqs,
    setup_requires=reqs,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Flask",
    ],
    python_requires=">=3.6",
)
