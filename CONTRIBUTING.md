# Contributing to Q-Shield

Thank you for your interest in contributing to Q-Shield! This guide will help you understand how to contribute effectively to the project.

## Table of Contents
1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Code Standards](#code-standards)
4. [Testing Requirements](#testing-requirements)
5. [Commit Guidelines](#commit-guidelines)
6. [Pull Request Process](#pull-request-process)
7. [Issue Reporting](#issue-reporting)
8. [Documentation](#documentation)

---

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (optional)
- Git

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/q-shield.git
cd q-shield

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt
pip install -e ".[dev]"  # Install with development extras

# Set up pre-commit hooks
pip install pre-commit
pre-commit install

# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -m app.db.database
```

### Verify Setup

```bash
# Run health check
pytest tests/unit/test_health.py

# Run API in dev mode
uvicorn app.main:app --reload

# Access API
curl http://localhost:8000/health
```

---

## Development Workflow

### 1. Choose or Create an Issue

```bash
# Check existing issues
# https://github.com/yourusername/q-shield/issues

# If creating new issue, include:
# - Clear title
# - Description of problem/feature
# - Expected behavior
# - Steps to reproduce (if bug)
# - Environment details
```

### 2. Create Feature Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/descriptive-name
# or for bug fix:
git checkout -b fix/issue-description
# or for documentation:
git checkout -b docs/what-you-added
```

**Branch Naming Convention**:
- `feature/` - New feature
- `fix/` - Bug fix
- `docs/` - Documentation
- `test/` - Test additions
- `refactor/` - Code refactoring
- `perf/` - Performance improvement

### 3. Make Changes

```bash
# Make your changes
# Run tests frequently
pytest

# Check types
mypy app/

# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Check style
flake8 app/ tests/

# All in one:
pre-commit run --all-files
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add PQC assessment endpoint"
```

See [Commit Guidelines](#commit-guidelines) for message format.

### 5. Push and Create Pull Request

```bash
git push origin feature/descriptive-name
# Visit GitHub and create Pull Request
```

---

## Code Standards

### Python Style Guide

Follow PEP 8 with these tools:

```bash
# Format with Black (80-char lines)
black --line-length=100 app/

# Check style
flake8 app/ --max-line-length=100

# Type checking
mypy app/

# Linting
pylint app/
```

### Code Organization

```
app/
├── api/
│   └── v1/
│       └── endpoints/
│           ├── __init__.py     # Router aggregation
│           ├── assets.py       # Asset endpoints
│           ├── scans.py        # Scan endpoints
│           └── assess.py       # Assessment endpoints
├── services/
│   ├── discovery/
│   │   └── tls_fingerprint.py  # Real TLS scanning
│   ├── pqc/
│   │   └── pqc_validator.py    # PQC assessment
│   ├── risk/
│   │   └── risk_scoring.py     # Risk calculation
│   ├── cbom/
│   │   └── cbom_generator.py   # CBOM export
│   ├── certificate/
│   │   └── certificate_engine.py  # Certificate issuance
│   └── compliance/
│       └── compliance_engine.py # Compliance mapping
├── models/
│   └── models.py               # SQLAlchemy ORM models
├── schemas/
│   └── schemas.py              # Pydantic request/response models
├── db/
│   └── database.py             # Database setup
├── core/
│   ├── config.py               # Settings
│   ├── security.py             # JWT, passwords
│   └── logging.py              # Logging setup
└── main.py                     # FastAPI app factory
```

### Docstring Format

Use Google-style docstrings:

```python
def calculate_risk_score(tls_config: TLSConfiguration) -> RiskScoreBreakdown:
    """Calculate cryptographic risk score.
    
    Analyzes TLS configuration against security best practices and
    generates a 0-100 risk score with component breakdown.
    
    Args:
        tls_config: TLS configuration from fingerprinting
        
    Returns:
        RiskScoreBreakdown with total score, severity, and components
        
    Raises:
        ValueError: If configuration is invalid
        
    Example:
        >>> config = TLSConfiguration(...)
        >>> score = calculate_risk_score(config)
        >>> print(f"Risk: {score.total_score}/100 ({score.severity})")
    """
```

### Type Hints

Always use type hints:

```python
from typing import Optional, List, Dict

async def scan_asset(
    asset_id: str,
    timeout_seconds: int = 30
) -> Optional[ScanResult]:
    """Scan asset for cryptographic configuration."""
    
def batch_scan(
    asset_ids: List[str],
    options: Dict[str, bool] = None
) -> List[ScanResult]:
    """Scan multiple assets in parallel."""
```

### Error Handling

Use specific exceptions:

```python
from fastapi import HTTPException, status

# Good
async def get_asset(asset_id: str, session: AsyncSession):
    asset = await session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found"
        )
    return asset

# Avoid
try:
    asset = await session.get(Asset, asset_id)
except:
    return None  # Too generic
```

---

## Testing Requirements

### Unit Tests

Test individual functions with mocked dependencies:

```python
# tests/unit/test_pqc_validator.py
import pytest
from app.services.pqc.pqc_validator import PQCValidator

@pytest.fixture
def validator():
    return PQCValidator()

def test_detect_ml_kem_512(validator):
    """Test detection of ML-KEM-512 algorithm"""
    tls_config = {
        "cipher_suites": ["TLS_MLKEM512_RSA_WITH_AES_256_GCM_SHA384"]
    }
    
    algorithms = validator._detect_pqc(tls_config)
    
    assert any(algo.name == "ML-KEM-512" for algo in algorithms)

@pytest.mark.asyncio
async def test_calculate_risk_score_invalid_config():
    """Test error handling for invalid config"""
    with pytest.raises(ValueError):
        await validator.assess_tls_configuration(None)
```

### Integration Tests

Test API endpoints with real database:

```python
# tests/integration/test_assets_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_asset(client: AsyncClient, token: str):
    """Test asset creation endpoint"""
    response = await client.post(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "hostname": "test.example.com",
            "port": 443,
            "description": "Test asset"
        }
    )
    
    assert response.status_code == 201
    assert response.json()["hostname"] == "test.example.com"
```

### Test Coverage

Maintain >85% coverage:

```bash
# Run tests with coverage report
pytest --cov=app --cov-report=html

# View report
open htmlcov/index.html
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_pqc_validator.py

# Run tests matching pattern
pytest -k "test_pqc"

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific marker
pytest -m "asyncio"
```

---

## Commit Guidelines

### Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Test addition/modification

**Scope**: Component affected (pqc, risk, cbom, api, etc.)

**Subject**: 
- Imperative mood ("add" not "adds" or "added")
- Don't capitalize first letter
- No period at end
- Max 50 characters

**Body** (optional):
- Explain what and why, not how
- Wrap at 72 characters
- Separate from subject with blank line

**Footer** (optional):
- Reference issues: `Fixes #123`
- Breaking changes: `BREAKING CHANGE: description`

### Examples

```bash
# Feature
git commit -m "feat(pqc): detect ML-DSA algorithms in TLS"

# Bug fix
git commit -m "fix(risk): correct severity calculation for TLS 1.1

Severity was incorrectly assigned penalty of 30 instead of 50.
Updated calculation to match NIST guidelines.

Fixes #456"

# Documentation
git commit -m "docs: add PQC migration timeline"

# Test
git commit -m "test(compliance): add RBI CSF control validation"
```

---

## Pull Request Process

### Before Submitting

1. **Update main branch**
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Run full test suite**
   ```bash
   pytest --cov=app
   black app/ tests/
   mypy app/
   flake8 app/
   ```

3. **Update documentation** if needed
   ```bash
   # If adding new endpoint, update docs/API.md
   # If changing architecture, update docs/ARCHITECTURE.md
   ```

4. **Create PR on GitHub**

### PR Title and Description

**Title Format**:
```
[TYPE] Short description

Examples:
[FEATURE] Add PQC certificate validation
[BUG FIX] Correct risk score calculation for hybrid TLS
[DOCS] Update API deployment guide
```

**Description Template**:
```markdown
## Description
Brief explanation of changes and why they're needed.

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Breaking change
- [ ] Documentation update

## How Has This Been Tested?
Describe testing approach:
- Unit tests: [describe]
- Integration tests: [describe]
- Manual testing: [describe]

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Commit messages follow guidelines

## Related Issues
Fixes #123
Relates to #456

## Screenshots (if applicable)
Screenshots of dashboard changes, etc.
```

### Code Review Process

**Reviewers** will check for:
- Code quality and style
- Test coverage
- Security issues
- Performance implications
- Documentation completeness

**Addressing Feedback**:
```bash
# Make requested changes
# Commit with meaningful message
git add .
git commit -m "refactor: address PR review comments"

# Don't force push; let history show conversation
git push origin feature/name
```

---

## Issue Reporting

### Bug Report Template

```markdown
## Description
Brief description of the bug

## Reproduction Steps
1. Step one
2. Step two
3. Step three

## Expected Behavior
What should happen

## Actual Behavior
What actually happened

## Error Message/Logs
```
error message or logs
```

## Environment
- OS: [e.g., macOS, Ubuntu 22.04]
- Python: [e.g., 3.11.0]
- Q-Shield Version: [e.g., 0.1.0]

## Screenshots
If applicable, add screenshots

## Additional Context
Any other context
```

### Feature Request Template

```markdown
## Description
What functionality do you want?

## Problem It Solves
Existing problem or use case

## Proposed Solution
How should it work?

## Alternatives Considered
Other approaches considered

## Value/Benefit
Why is this valuable?

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

---

## Documentation

### When to Document

- New public APIs or endpoints
- Configuration options
- Deployment procedures
- Breaking changes
- New architectural decisions

### Documentation Files

- `README.md` - Project overview
- `docs/ARCHITECTURE.md` - System design
- `docs/API.md` - API reference
- `docs/DEVELOPMENT.md` - Developer setup
- `docs/DEPLOYMENT.md` - Deployment guide
- `docs/SECURITY.md` - Security practices

### Adding an Endpoint

1. **Update `docs/API.md`**:
   - Add endpoint description
   - Show request/response format
   - Include example cURL command
   - Document error cases

2. **Add docstring to function**:
   ```python
   async def list_assets(...):
       """List all assets with optional filtering.
       
       Returns paginated list of assets belonging to current organization.
       """
   ```

3. **Update README if major feature**

---

## Questions or Need Help?

- **Discussions**: https://github.com/yourusername/q-shield/discussions
- **Issues**: https://github.com/yourusername/q-shield/issues
- **Email**: dev@q-shield.example.com
- **Documentation**: Check existing docs in `/docs` folder

---

## Code of Conduct

- Be respectful and inclusive
- Assume good intent
- Provide constructive feedback
- Report inappropriate behavior

---

Thank you for contributing to Q-Shield! 🚀

Your help makes Q-Shield better for everyone.
