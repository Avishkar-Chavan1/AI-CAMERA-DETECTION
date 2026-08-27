$ErrorActionPreference = "Stop"

python -m pytest
python -m ruff check .
