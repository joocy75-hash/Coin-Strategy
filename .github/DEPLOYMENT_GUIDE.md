# GitHub Deployment Guide

## 🚀 Quick Deploy to GitHub

### Step 1: Create GitHub Repository

```bash
# Go to https://github.com/new
# Repository name: strategy-research-lab
# Visibility: Public or Private
# Click "Create repository"
```

### Step 2: Connect Local Repo to GitHub

```bash
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/strategy-research-lab.git

# Push to GitHub
git push -u origin main
```

### Step 3: Set Up Secrets (for LLM features)

1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add:
   - Name: `ANTHROPIC_API_KEY`
   - Value: `sk-ant-api03-...`

### Step 4: Enable GitHub Actions

1. Go to repository → Actions tab
2. Click "I understand my workflows, go ahead and enable them"
3. Workflows will run automatically on push

---

## ✅ CI/CD Pipeline

Our GitHub Actions workflow includes:

1. **Lint** - Code quality check (ruff, black)
2. **Test** - Unit tests and import validation
3. **Deploy** - Create deployment package

### Workflow Triggers

- Push to `main` or `develop` branch
- Pull requests to `main`

### What Gets Deployed

- All `src/` code
- `requirements.txt`
- Documentation (`*.md`)
- Packaged as `deploy.tar.gz`

---

## 📦 Manual Deployment

If you prefer manual deployment:

```bash
# 1. Create package
tar -czf strategy-research-lab.tar.gz \
  src/ \
  requirements.txt \
  PHASE4_README.md \
  examples/

# 2. Upload to server
scp strategy-research-lab.tar.gz user@server:/path/

# 3. Extract and install
ssh user@server
cd /path
tar -xzf strategy-research-lab.tar.gz
pip install -r requirements.txt
```

---

## 🔒 Security Notes

- Never commit API keys to the repository
- Use GitHub Secrets for sensitive data
- The workflow file is secure (no untrusted input injection)

---

## 📊 Monitoring Deployments

View deployment status:
- GitHub Actions tab → Latest workflow run
- Artifacts section → Download `deployment` package

---

## 🆘 Troubleshooting

**Issue**: Workflow fails on test job
- Check Python version compatibility
- Ensure all dependencies in `requirements.txt`

**Issue**: Import errors
- Verify `src/converter/llm/__init__.py` exports
- Check file permissions

**Issue**: Deployment artifact missing
- Workflow only creates artifacts on `main` branch
- Check branch protection rules

---

**Last Updated**: 2026-01-04
