# Development - Contributing

Issues and pull requests are more than welcome: https://github.com/developmentseed/tipgstac/issues

**dev install**

```bash
git clone https://github.com/developmentseed/tipgstac.git
cd tipgstac
python -m pip install -e .["test,dev"]
```

You can then run the tests with the following command:

```sh
python -m pytest --cov tipgstac --cov-report term-missing --asyncio-mode=strict
```

**pre-commit**

This repo is set to use `pre-commit` to run *isort*, *flake8*, *pydocstring*, *black* ("uncompromising Python code formatter") and mypy when committing new code.

```bash
# Install pre-commit command
$ pip install pre-commit

# Setup pre-commit withing your local environment
$ pre-commit install
```
