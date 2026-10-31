# Contributing

## Development Setup

This project uses `uv` for dependency management.

```bash
uv sync --dev
```

## Test-Driven Development

Use the red-green-refactor workflow for every small change:

1. Write a test that describes the next piece of behaviour.
2. Run it and confirm that it fails for the expected reason.
3. Write the smallest implementation that makes it pass.
4. Refactor for readability before starting the next test.

Every feature and bug fix must be backed by a test.

## Coverage

The integration must keep 100% line and branch coverage for
`custom_components/sunset`.

- Tests themselves are not included in the coverage measurement.
- Test public contracts such as config entry setup, entities, services,
  and public controller/calculator APIs.
- Do not assert private `_` helpers or private state. If a scenario
  truly cannot be reached without private access, mark the test with
  `@pytest.mark.internal` and explain why.
- Do not use blanket coverage exclusions. Only use an inline
  `# pragma: no cover` comment with a reason for genuinely unreachable
  code, such as `if TYPE_CHECKING:` blocks.
- Prefer refactoring for testability, for example by injecting a clock,
  over suppressing an untestable branch.

## Checks

Run the same checks as CI before committing:

```bash
uv run ruff check custom_components tests
uv run ruff format --check custom_components tests
uv run ty check custom_components tests
uv run pytest
```

The pytest configuration enables branch coverage and fails below 100%.
