# Updating the Documentation

This project uses [Jupyter Book](https://jupyterbook.org/) to generate its documentation. 

If you would like to contribute to the documentation, follow the instructions below to build the book locally and verify your changes before opening a pull request.

## Local Build Instructions

1. Ensure you have installed the project with its `dev` dependencies (which includes `jupyter-book`). If you haven't yet, run:
   ```bash
   pip install -e ".[dev]"
   ```

2. Make your edits to the `.md` or `.ipynb` files within the `docs/` directory.
   - User documentation goes in `docs/user/`.
   - Developer documentation goes in `docs/developer/`.
   - Be sure to update `docs/_toc.yml` if you add or remove files.

3. Build the book by running the following command from the root of the repository:
   ```bash
   jupyter-book build docs/
   ```

4. If the build succeeds, you can preview the documentation by opening the generated HTML file in your browser:
   ```bash
   # On macOS:
   open docs/_build/html/index.html
   
   # On Linux:
   xdg-open docs/_build/html/index.html
   
   # On Windows:
   start docs/_build/html/index.html
   ```

## Deployment

The documentation is automatically built and deployed to GitHub Pages via a GitHub Actions workflow whenever changes are merged into the `main` branch.
