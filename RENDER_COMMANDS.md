# Render Deployment Commands - AxiomOS Web Service

## 🏗️ **Build Command**

```bash
uv sync --frozen && uv cache prune --ci
```

**Why this command:**

- `uv sync --frozen`: Uses the locked `uv.lock` file for reproducible builds
- `uv cache prune --ci`: Optimizes cache for CI/CD environments, reducing deployment size
- Much faster than `pip install -r requirements.txt` (typically 3-5x faster)
- Ensures exact dependency versions for production stability

## 🚀 **Start Command**

```bash
uv run python fastapi_app.py
```

**Why this command:**

- `uv run python`: Uses the locked virtual environment from the build step
- Ensures the exact same dependencies used during build are used at runtime
- More efficient than system Python with pip-installed packages
- Follows uv's recommended production pattern

## 📋 **Complete render.yaml Configuration**

```yaml
services:
  - type: web
    name: axiomos-web
    env: python
    runtime: uv
    plan: starter
    buildCommand: "uv sync --frozen && uv cache prune --ci"
    startCommand: "uv run python fastapi_app.py"
    healthCheckPath: /health
    
    envVars:
      - key: PYTHON_VERSION
        value: 3.13
      - key: GROQ_API_KEY
        sync: false
      # ... other environment variables
```

## ⚡ **Performance Benefits**

### vs Traditional pip setup:
- **Build Speed**: 3-5x faster dependency installation
- **Deploy Size**: Smaller due to cache pruning
- **Reliability**: Locked dependencies prevent version conflicts
- **Reproducibility**: Exact same environment every deployment

### Cache Optimization:
- `--ci` flag optimizes for container environments
- Prunes unnecessary cache files
- Reduces deployment artifact size
- Maintains speed benefits for subsequent deployments

## 🔧 **Alternative Options**

### If you prefer pip (not recommended):
```yaml
buildCommand: "pip install -r requirements.txt"
startCommand: "python fastapi_app.py"
```

### For local development:
```bash
# Build
uv sync --frozen

# Run
uv run python fastapi_app.py
```

## ✅ **Verification Commands**

### Test locally before deploying:
```bash
# Test build process
uv sync --frozen && uv cache prune --ci

# Test start command
uv run python fastapi_app.py

# Check environment
uv run python -c "import fastapi, groq; print('✅ Dependencies OK')"
```

### After deployment:
- Visit `/health` endpoint to verify services
- Check Render logs for build/start success
- Test chat functionality in web interface

## 🚨 **Important Notes**

1. **uv.lock Required**: The `--frozen` flag requires the `uv.lock` file (already generated)
2. **Runtime Specification**: `runtime: uv` tells Render to use uv environment
3. **Cache Optimization**: `--ci` flag is crucial for production deployments
4. **Consistency**: Use same pattern in local development and production

---

## 🎯 **Summary**

**Build Command**: `uv sync --frozen && uv cache prune --ci`
**Start Command**: `uv run python fastapi_app.py`

This configuration provides the fastest, most reliable deployment for AxiomOS on Render with modern Python package management.