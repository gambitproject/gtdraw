# Updating the Documentation

This project uses [Jupyter Book](https://jupyterbook.org/) to generate its documentation. 

If you would like to contribute to the documentation, follow the instructions below to build the book locally and verify your changes before opening a pull request.

## Local Build Instructions

::: {important}
To build the documentation locally, you **must use Python 3.13 or higher**. This project uses Jupyter Book 2.0+, which is optimized for modern Python environments.
:::

1. Ensure you have installed the project with its `dev` dependencies (which includes `jupyter-book`). If you haven't yet, run:
   ```bash
   pip install -e ".[dev]"
   ```

2. Make your edits to the `.md` or `.ipynb` files within the `docs/` directory.
   - User documentation goes in `docs/`.
   - Developer documentation goes in `docs/developer/`.
   - Be sure to update `docs/myst.yml` if you add or remove files.

3. Preview the documentation in your browser at `http://localhost:3000/`:
   ```bash
   cd docs
   jupyter-book start
   ```

## Deployment

The documentation is automatically built and deployed to GitHub Pages via a GitHub Actions workflow whenever changes are merged into the `main` branch.
