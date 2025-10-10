Contributing to App Migrator

We love your input! We want to make contributing to App Migrator as easy and transparent as possible.
Development Setup

    Fork the repository

    Clone your fork:
    bash

bench get-app https://github.com/rogerboy38/app_migrator

Create a feature branch:
bash

git checkout -b feature/amazing-feature

Development Guidelines
Code Style

    Follow PEP 8 for Python code

    Use meaningful variable names

    Add docstrings to all functions

    Include type hints where possible

Testing

    Test all new features

    Ensure existing functionality still works

    Test with different Frappe versions

Pull Request Process

    Update documentation if needed

    Add tests for new functionality

    Ensure all tests pass

    Submit pull request with clear description

Architecture
Core Components

    commands/ - CLI command implementations

    migrator.py - Core migration engine

    discovery/ - App structure analysis (future)

Adding New Commands

    Add command function in commands/__init__.py

    Register in commands list

    Update documentation

Feature Requests

We welcome feature requests! Please use the issue template and include:

    Use case description

    Expected behavior

    Potential implementation approach
    
