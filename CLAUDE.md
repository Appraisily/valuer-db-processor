<<<<<<< HEAD
# CLAUDE.md - Development Guide

## Commands
- Run server: `uvicorn src.main:app --reload`
- Run tests: `python test_app.py`
- Code formatting: `black .`
- Import sorting: `isort .`
- Type checking: `mypy src`
- Run all checks: `black . && isort . && mypy src`
- Set up sample images: `python setup_sample_images.py`
- Test image handling: `python test_image.py`

## Code Style
- **Imports**: stdlib first, third-party second, local imports last
- **Formatting**: 4-space indentation, max 100 chars per line
- **Naming**: snake_case (variables/functions), PascalCase (classes)
- **Types**: Full type annotations required on functions and parameters
- **Error handling**: Use try/except with specific exceptions, log errors
- **Documentation**: Docstrings for all public functions and classes
- **Architecture**: Follow service-based model organization (models, services, utils)

## Project Organization
- Models are Pydantic (API) and SQLAlchemy (database) classes
- Business logic in services/ directory
- Configuration in config.py with environment variable support
- Utilities in utils/ for cross-cutting concerns

## Image Handling
- In development mode, sample images are stored in ./local_images
- The system first checks for local images before trying to download from remote
- Image downloading follows a multi-stage fallback approach:
  1. Try downloading from the primary image URL with browser-like headers
  2. Try multiple alternative CDN URLs (media.invaluable.com, www.invaluable.com, cdn.invaluable.com)
  3. Try host header injection to bypass Cloudflare restrictions
  4. Try origin IP approach (accessing the website's origin IP directly)
  5. For development mode only: check for locally cached images
  6. Generate placeholder images with relevant information when all download attempts fail

### Testing Image Download
To test image handling, run:
  1. `python setup_sample_images.py` to create sample images
  2. `python test_image.py` to test the standard download, optimize, and save process 
  3. `python test_origin_ip.py` to test the origin IP bypass approach
  4. `python test_browser_approach.py` to test browser-like approaches
  5. `python test_fallback.py` to test the fallback mechanism

### Image Proxy Server
For more reliable image downloads, you can use the built-in proxy server:
  1. `python test_proxy_server.py` to start a local proxy server on port 8000
  2. Open your browser to http://localhost:8000 to see test images
  3. The proxy server will attempt to download images through multiple methods and save them locally

This proxy server approach allows you to:
- Test image downloads interactively through a browser
- Handle Cloudflare protections by leveraging your browser's session
- Cache downloaded images locally for future use
- Fall back to alternative URLs when the primary URL fails
- Generate placeholder images when all download attempts fail

### Headless Browser Approach
For automated image downloads that can bypass protection:
  1. Install Playwright dependencies: `pip install playwright && python -m playwright install`
  2. Run `python test_headless_browser.py` to test downloading with a headless browser
  3. This simulates a full browser session including cookies and JavaScript execution

### End-to-End Testing
For complete end-to-end testing, run:
  1. `uvicorn src.main:app --reload` to start the server
  2. `python test_process.py` to test the process endpoint with image handling
=======
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
>>>>>>> 2296ae64bae38ecfae3e327a8294e1749682a204
