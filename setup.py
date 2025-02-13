from setuptools import setup

setup(
    name='azure-cost-tracker',
    version="0.1.0",
    author="interittus13",
    author_email="",
    url="https://github.com/Interittus13/AzureCostTracker",
    description="A Python tool for tracking Azure subscription costs, generating reports, and sending automated email notifications.",
    packages=['src', 'src.services'],
    package_data={'': ['../templates/*.html']},
    include_package_data = True,
    install_requires=["jinja2", "requests", "python-dotenv"],
    entry_points="""
        [console_scripts]
        azure-cost-tracker=src.main:main
        """,
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.7",
)