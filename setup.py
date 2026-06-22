import os
from setuptools import setup

ROOT = os.path.dirname(__file__)
VERSION_FILE = os.path.join(ROOT, "src", "__version__.py")


def get_version():
    with open(VERSION_FILE, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("__version__"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("Unable to find version string.")


setup(
    name='azure-cost-tracker',
    version=get_version(),
    author="interittus13",
    author_email="",
    url="https://github.com/Interittus13/AzureCostTracker",
    description="A Python tool for tracking Azure subscription costs, generating reports, and sending automated email notifications.",
    packages=['src', 'src.services', 'src.services.report', 'src.services.snapshot', 'src.utils'],
    package_data={'': ['../templates/*.html', '../templates/components/*.html']},
    include_package_data=True,
    install_requires=[
        "jinja2",
        "requests",
        "python-dotenv",
        "cryptography",
        "weasyprint",
        "fastapi",
        "uvicorn",
        "httpx",
    ],
    entry_points="""
        [console_scripts]
        azure-cost-tracker=src.main:run
        act=src.main:run
        """,
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.7",
)
