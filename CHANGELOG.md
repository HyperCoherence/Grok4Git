# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Peer review system for pull requests, including commands to toggle and check status.
- Automatic code formatting (black, isort, autopep8) and security checks (safety, bandit) in CI workflow.

### Changed
- Revised command structure in chat.py and commands.py for streamlined user interactions.
- Updated natural language processing for GitHub operations and enhanced slash commands.
- Improved .env file handling in Config class and updated test cases.
- Refactored response display in chat.py for better formatting and readability.
- Enhanced README.md with detailed explanations, examples, and screenshot integration.
- Refactored code for improved type hinting, error handling, and readability across multiple files.
- Updated images (Screenshot_1.jpg and Screenshot_2.jpg).

### Fixed
- N/A

## [1.0.0] - 2025-07-13

### Added
- Initial release of Grok4Git with core features: natural language GitHub operations, repository management, file operations, pull requests, issues, and code search.
- Integration with Grok AI from xAI.
- CLI interface with slash commands.

### Changed
- N/A (initial release)

### Fixed
- N/A (initial release)