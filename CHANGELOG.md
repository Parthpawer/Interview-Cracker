# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **CI/CD**: GitHub Actions workflow (`.github/workflows/build.yml`) for automated Windows builds and releases.
- **Modular Structure**: Created `src/` directory with `core`, `ui`, and `utils` packages.
- **Configuration**: Dedicated `src/config.py` for environment variable management.
- **Styling**: External `styles.qss` file for application theming.
- **Entry Point**: New `main.py` entry point.

### Changed
- **Refactoring**: Split the monolithic `another.py` into:
    - `src/core/audio.py`: Azure Speech transcription logic.
    - `src/core/gemini.py`: Google Gemini API integration.
    - `src/ui/main_window.py`: Main GUI implementation.
    - `src/ui/widgets.py`: Custom widgets (e.g., secure combo box).
    - `src/utils/helpers.py`: Helper functions (markdown conversion, resource paths).
- **Build Spec**: Updated `AI-Assistant.spec` to support the new modular structure and include `styles.qss`.
- **Documentation**: Updated `README.md` to reflect the new architecture and deployment instructions.

### Fixed
- **Resource Loading**: Implemented `resource_path` helper to correctly load assets (like `styles.qss`) in the frozen PyInstaller executable.
- **Config**: Fixed stale configuration usage in `GeminiClient` to ensure settings updates apply immediately.
