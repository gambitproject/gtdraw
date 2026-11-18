# Local Development & Testing

## Installation for Development

To set up the project for development, clone the repository and install it along with the `dev` extra dependencies:

```bash
git clone https://github.com/gambitproject/gtdraw
cd gtdraw
pip install -e ".[dev]"
```

You'll also need to follow the rest of the steps on the [installation](installation) page for LaTeX and other requirements.

## Testing

The project includes a comprehensive test suite using `pytest`. 

To run all tests:
```bash
pytest tests/ -v
```

To run tests with coverage reporting:
```bash
pytest tests/ --cov=gtdraw --cov-report=html
```

## Releases

To release a new version of `gtdraw`:

1. Update the version number in `pyproject.toml`, the only place it is written. `gtdraw.__version__` is read
   from the installed package's metadata, so reinstall (`pip install -e .`) to see a new version locally.
2. Create a pull request targeting the `main` branch with the change.
3. Once the pull request is approved and merged, update your local `main` branch:

    ```bash
    git checkout main
    git pull origin main
    ```

4. Create and push a new tag corresponding to the version:

    ```bash
    git tag vX.X.X
    git push origin tag vX.X.X
    ```

5. Finally, create a new Release on GitHub based on the pushed tag. Publishing the release starts the `Publish to
   PyPI` workflow, which runs the tests and stops if the tag, less its `v`, differs from the version in
   `pyproject.toml`, before anything is built or uploaded.
