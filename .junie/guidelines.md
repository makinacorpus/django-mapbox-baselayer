### Build & Configuration

Install dependencies in a virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Settings module for the test project: `test_mapbox_baselayer.settings` (auto-detected via `manage.py`). It uses SQLite with an in-memory database for tests.

### Running Tests

```bash
# All tests
python manage.py test mapbox_baselayer.tests --parallel

# Specific test module
python manage.py test mapbox_baselayer.tests.test_models

# Specific test case
python manage.py test mapbox_baselayer.tests.test_validators_example.ValidateRequiredTokenInTileUrlTestCase

# With coverage (via Makefile)
make coverage
```

Makefile targets: `make test` (optionally `test_name=...`), `make coverage`.

### Adding Tests

Place test files in `mapbox_baselayer/tests/` with the `test_` prefix. Use `django.test.TestCase` as the base class.

**Note:** The existing model/view tests (`test_models.py`, `test_views.py`) currently fail because migration `0013` added a non-nullable `external_id` field (`CharField(blank=True)`) without a default value, but the test factories/setUp methods don't supply it. When creating model instances in tests, provide `external_id=""` or fix the migration to include `default=""`.

Example test (`mapbox_baselayer/tests/test_validators_example.py` pattern):

```python
from django.core.exceptions import ValidationError
from django.test import TestCase

from mapbox_baselayer.validators import (
    validate_only_required_tokens_in_tile_url,
    validate_required_token_in_tile_url,
)


class ValidateRequiredTokenInTileUrlTestCase(TestCase):
    def test_valid_url(self):
        validate_required_token_in_tile_url(
            "https://example.com/{z}/{x}/{y}.png"
        )

    def test_missing_token_raises(self):
        with self.assertRaises(ValidationError):
            validate_required_token_in_tile_url("https://example.com/{z}/{x}.png")
```

### Code Style

- **Formatter/Linter:** Ruff (configured in `ruff.toml`), Black-compatible style.
- Line length: 88, indent: 4 spaces, double quotes.
- Run `make quality` (or `make lint` + `make format`) before committing.
- Target Python version: 3.9+.

### Project Layout

- `mapbox_baselayer/` — the Django app (models, views, admin, migrations, management commands, tests).
- `test_mapbox_baselayer/` — test project providing Django settings, URLs, and a small test app with a template.
- `manage.py` uses `test_mapbox_baselayer.settings` by default.

### Translations

```bash
make messages        # regenerate .po files
```

Locale files are in both `mapbox_baselayer/locale/` and `test_mapbox_baselayer/locale/` (en, fr).
