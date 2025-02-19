from setuptools import setup, find_packages

setup(
    name='metatools',
    version=0.2,
    description='Tools for exploring and analyzing tournament results',
    packages=find_packages(),

    author='Jesse Hatfield',

    package_data = {
        # Include the config file:
        'metatools': ['*.ini']
    },

    # Uses SQLAlchemy to interact with database
    install_requires=['SQLAlchemy >=0.9.8', 'scipy'],

    # Executable scripts
    entry_points={
        'console_scripts': [
            # tmi : Main entry point for computing arbitrary statistics
            'tmi = metatools.tmi:main',
            # generate : Automatically generate standard reports for recent tournaments
            'generate = metatools.generate:main'
        ],
        'gui_scripts': []  # None of these yet
    }
)
