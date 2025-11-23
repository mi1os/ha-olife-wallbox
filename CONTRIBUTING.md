# Contributing to Olife Energy Wallbox Integration

Thank you for considering contributing to the Olife Energy Wallbox integration! Here's how you can help.

## Development Environment Setup

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use .venv\Scripts\activate
   pip install -r requirements_dev.txt
   ```

## Making Changes

1. Create a new branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes
3. Test your changes locally
4. Run linting tools:
   ```bash
   flake8 custom_components/
   ```

5. Commit your changes using [Conventional Commits](https://www.conventionalcommits.org/):
   ```bash
   # For bug fixes (patch version bump: 0.9.8 -> 0.9.9)
   git commit -m "fix: resolve connection timeout issue"
   
   # For new features (minor version bump: 0.9.8 -> 0.10.0)
   git commit -m "feat: add new energy monitoring sensor"
   
   # For breaking changes (major version bump: 0.9.8 -> 1.0.0)
   git commit -m "feat!: remove deprecated daily sensors
   
   BREAKING CHANGE: Daily/monthly/yearly sensors removed, use Energy Dashboard instead"
   
   # For documentation changes (no version bump)
   git commit -m "docs: update installation instructions"
   
   # For code refactoring (no version bump)
   git commit -m "refactor: simplify error handling logic"
   ```

### Commit Message Format

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automated versioning and changelog generation.

**Format**: `<type>(<scope>): <subject>`

**Types**:
- `feat:` - New feature (triggers minor version bump)
- `fix:` - Bug fix (triggers patch version bump)
- `docs:` - Documentation only changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring without functionality changes
- `perf:` - Performance improvements
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks, dependency updates

**Breaking Changes**: Add `!` after type or `BREAKING CHANGE:` in footer to trigger major version bump

**Examples**:
```bash
feat(sensor): add phase voltage monitoring
fix(switch): correct automatic charging toggle state
docs(readme): add HACS installation instructions
perf(modbus): reduce connection pooling overhead
```

## Pull Request Process

1. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Submit a pull request from your branch to the main repository
3. Update the README.md or documentation if needed
4. The maintainers will review your PR and may request changes

## Release Process

**Releases are fully automated!** 🎉

When your PR is merged to `main`:
1. Semantic-release analyzes commit messages
2. Determines version bump based on commit types
3. Updates `manifest.json` automatically
4. Generates `CHANGELOG.md` automatically
5. Creates GitHub release with ZIP file
6. Tags the release

**You don't need to do anything!** Just use conventional commits.

## Code Style

- Follow the [Home Assistant development guidelines](https://developers.home-assistant.io/docs/development_guidelines)
- Use consistent formatting
- Include docstrings for new functions and classes
- Add type hints where appropriate

## Testing

- Test your changes with actual hardware if possible
- Test with Home Assistant in a development environment

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License. 