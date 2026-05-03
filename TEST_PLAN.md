# App Migrator - CI/CD Test Plan
## Frappe V16 Migration + Sandbox → Test/Prod Docker Pipeline

**Document Version:** 1.0
**Last Updated:** 2026-05-03
**Target:** App Migrator v9.0.0+ with Frappe V16

---

## 1. Test Objectives

This test plan validates the complete CI/CD pipeline:
1. **Frappe V16 Compatibility**: Verify app_migrator works with Frappe V16 (Python 3.14+, pyproject.toml)
2. **GitHub Actions CI**: Validate linting, testing, and Docker image building
3. **Test Docker Deployment**: Verify automatic deployment to test environment
4. **Production Docker Deployment**: Validate manual promotion with blue-green deployment
5. **Rollback Capability**: Ensure safe rollback from failed deployments

---

## 2. Test Environments

| Environment | Purpose | Trigger | URL |
|-------------|---------|---------|-----|
| **Local Dev** | Development sandbox (Frappe Bench) | Manual | localhost:8000 |
| **CI Pipeline** | Lint, Test, Build | Every PR/push | GitHub Actions |
| **Test Docker** | Staging verification | Push to main | test.appmigrator.local |
| **Production** | Live environment | Manual dispatch | appmigrator.com |

---

## 3. Test Scenarios

### 3.1 Frappe V16 Compatibility Tests

| Test ID | Test Case | Expected Result | Verification Method |
|---------|-----------|-----------------|---------------------|
| **V16-01** | pyproject.toml valid syntax | No parsing errors | `flit validate` |
| **V16-02** | Python 3.14+ requirement | Correctly declared | Check requires-python |
| **V16-03** | flit_core build backend | Properly configured | Build succeeds |
| **V16-04** | Frappe dependency declared | `>=16.0.0-dev` | Check pyproject.toml |
| **V16-05** | App installs on Frappe V16 bench | No errors | `bench install-app` |

### 3.2 GitHub Actions CI Tests

| Test ID | Test Case | Expected Result | Verification Method |
|---------|-----------|-----------------|---------------------|
| **CI-01** | Ruff linting passes | No lint errors | GitHub Actions log |
| **CI-02** | Ruff formatting check | Files properly formatted | GitHub Actions log |
| **CI-03** | Python unit tests | All tests pass | Test results artifact |
| **CI-04** | Frappe integration tests | App commands available | bench output |
| **CI-05** | Docker image build | Image created & pushed | Registry verification |
| **CI-06** | pyproject.toml validation | Config valid | flit validate output |

### 3.3 Test Docker Deployment Tests

| Test ID | Test Case | Expected Result | Verification Method |
|---------|-----------|-----------------|---------------------|
| **TEST-01** | Auto-deploy on push | Test container updated | Container image tag |
| **TEST-02** | Health check endpoint | Returns 200 OK | curl test |
| **TEST-03** | bench app-migrator health | Command executes | SSH + command output |
| **TEST-04** | Database migration | Completed without errors | Migration logs |
| **TEST-05** | Redis connectivity | Cache working | redis-cli ping |
| **TEST-06** | WebSocket available | Socket.IO responding | Connection test |

### 3.4 Production Docker Deployment Tests

| Test ID | Test Case | Expected Result | Verification Method |
|---------|-----------|-----------------|---------------------|
| **PROD-01** | Manual trigger workflow | Deployment starts | GitHub Actions run |
| **PROD-02** | Version input validation | Correct tag used | Image tag check |
| **PROD-03** | Pre-deployment backup | Backup created | Backup file exists |
| **PROD-04** | Blue-green switch | Traffic routes correctly | curl health check |
| **PROD-05** | Post-deploy migration | Migrates successfully | bench migrate output |
| **PROD-06** | Rollback capability | Returns to previous version | Image rollback test |

---

## 4. Test Execution Checklist

### Phase 1: Local Development Verification
```bash
# 1. Update bench to latest version
bench --version  # Should be 5.22.6+
pip install --upgrade frappe-bench

# 2. Verify pyproject.toml
cd app_migrator
flit validate

# 3. Test linting locally
pip install ruff
ruff check ./app_migrator

# 4. Initialize test bench with Frappe V16
bench init frappe-bench-v16 --frappe-branch version-16 --python python3.14
cd frappe-bench-v16
bench get-app frappe --branch version-16
bench get-app ../app_migrator
bench new-site test.v16.local --db-name test_v16 --admin-password admin
bench --site test.v16.local install-app frappe
bench --site test.v16.local install-app app_migrator

# 5. Test app commands
bench app-migrator health
bench app-migrator diagnose --site test.v16.local
```

### Phase 2: GitHub Actions Verification
```bash
# 1. Create a test PR
git checkout -b test/verify-ci
git add .
git commit -m "test: Verify CI pipeline"
git push origin test/verify-ci
# Open PR to main - CI should trigger

# 2. Check GitHub Actions tab
# - Lint job should pass
# - Test job should complete
# - Build job should create image
```

### Phase 3: Test Environment Verification
```bash
# 1. Push to main (triggers deploy-test.yml)
git checkout main
git merge test/verify-ci
git push origin main

# 2. Check GitHub Actions for deploy-test workflow

# 3. SSH to test server and verify
ssh test-server
docker ps | grep app-migrator
docker logs <container> --tail=50
curl -f http://localhost/api/method/health

# 4. Verify app commands
docker exec <container> bench app-migrator health
```

### Phase 4: Production Deployment Verification
```bash
# 1. Go to GitHub Actions > deploy-prod
# 2. Click "Run workflow"
# 3. Enter version (e.g., sha-abc1234)
# 4. Enable "Create full backup"
# 5. Click "Run workflow"

# 6. Monitor deployment logs

# 7. Verify after deployment
curl -f https://appmigrator.com/api/method/health
docker exec <container> bench --site <site> list-apps
```

---

## 5. Success Criteria

| Phase | Criteria | Status |
|-------|----------|--------|
| **Frappe V16** | pyproject.toml validates | ☐ |
| **Frappe V16** | App installs on V16 bench | ☐ |
| **CI Pipeline** | All 6 CI jobs pass | ☐ |
| **Test Deploy** | Auto-deploys on main push | ☐ |
| **Test Deploy** | Health check returns 200 | ☐ |
| **Prod Deploy** | Manual trigger works | ☐ |
| **Prod Deploy** | Blue-green switches traffic | ☐ |
| **Rollback** | Can revert to previous version | ☐ |

**Overall Goal**: 8/8 criteria must pass

---

## 6. Known Issues & Troubleshooting

### Issue 1: Python 3.14 not available
**Solution**: Use pyenv or docker image with Python 3.14

### Issue 2: flit validation fails
**Solution**: Ensure `[build-system]` and `[project]` sections are valid TOML

### Issue 3: Docker build fails
**Solution**: Check `apps.json` format and GitHub token permissions

### Issue 4: SSH deployment fails
**Solution**: Verify SSH keys in GitHub Secrets and server authorized_keys

### Issue 5: Health check timeout
**Solution**: Increase start_period in docker-compose or check app logs

---

## 7. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Reviewer | | | |
| DevOps | | | |

---

## Appendix A: GitHub Secrets Required

```
TEST_HOST=test.server.com
TEST_USER=deploy
TEST_SSH_KEY=<private_key>
PROD_HOST=prod.server.com
PROD_USER=deploy
PROD_SSH_KEY=<private_key>
PROD_SITE_NAME=appmigrator.com
PROD_URL=https://appmigrator.com
AWS_BACKUP_BUCKET=<bucket_name>
```

## Appendix B: Docker Image Registry

- **Image Name**: `ghcr.io/rogerboy38/app_migrator`
- **Tags**: `latest`, `sha-<commit>`, `v<version>`
- **Multi-arch**: linux/amd64, linux/arm64