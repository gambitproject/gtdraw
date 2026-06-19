# Local Development & Testing

## Installation for Development

To set up the project for development, clone the repository and install it along with the `dev` extra dependencies:

```bash
git clone https://github.com/gambitproject/draw_tree
cd efgviz
pip install -e ".[dev]"
```

## Testing

The project includes a comprehensive test suite using `pytest`. 

To run all tests:
```bash
pytest tests/ -v
```

To run tests with coverage reporting:
```bash
pytest tests/ --cov=efgviz --cov-report=html
```

## Releases

To release a new version of `efgviz`:

1. Update the version number in `pyproject.toml`.
2. Update the version number in `src/efgviz/__init__.py`.
3. Create a pull request targeting the `main` branch with the changes.
4. Once the pull request is approved and merged, update your local `main` branch:

    ```bash
    git checkout main
    git pull origin main
    ```

5. Create and push a new tag corresponding to the version:

    ```bash
    git tag vX.X.X
    git push origin tag vX.X.X
    ```

6. Finally, create a new Release on GitHub based on the pushed tag.
