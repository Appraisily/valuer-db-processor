# Development Guidelines

## Commands
- **Run Server**: `uvicorn src.main:app --reload` or `python run_app.py`
- **Run Tests**: `pytest test_app.py -v`
- **Run Single Test**: `pytest test_app.py::test_function_name -v`
- **Format Code**: `black .`
- **Sort Imports**: `isort .`
- **Type Check**: `mypy src/`

## Code Style
- **Imports**: Use isort with sections stdlib, third-party, local
- **Formatting**: Black with default line length (88 characters)
- **Types**: Always use type annotations; Pydantic for data models
- **Naming**:
  - Classes: PascalCase
  - Functions/variables: snake_case
  - Constants: UPPER_SNAKE_CASE
- **Error Handling**: Use custom AppException from utils.errors
- **Logging**: Use structured logging via utils.logging
- **Comments**: Docstrings for all public functions and classes
- **Architecture**: Follow service-oriented design with clear separation between models, services, and utilities