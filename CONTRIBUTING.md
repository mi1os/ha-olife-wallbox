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

5. Commit your changes:
   ```bash
   git commit -m "Description of changes"
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

When creating a new release:

1. Use the release script:
   ```bash
   ./scripts/release.sh 0.x.y
   ```

2. Push the changes and tag:
   ```bash
   git push origin main
   git push origin vX.Y.Z
   ```

3. GitHub Actions will automatically create the release

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