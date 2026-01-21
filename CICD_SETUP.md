# CI/CD Setup Guide

## GitHub Actions Workflow for Development

Workflow này tự động thực hiện các bước sau khi có code mới được push lên repository:

### 🔄 Workflow Stages

1. **Lint** - Kiểm tra chất lượng code
   - Black (code formatting)
   - isort (import sorting)
   - Flake8 (linting)

2. **Test** - Chạy unit tests
   - Setup PostgreSQL test database
   - Chạy pytest với coverage report
   - Upload coverage to Codecov (optional)

3. **Build** - Build Docker image
   - Build Docker image từ Dockerfile
   - Push image lên GitHub Container Registry (GHCR)
   - Tag với branch name và commit SHA

4. **Deploy** - Deploy lên development server
   - SSH vào server
   - Pull latest code
   - Pull latest Docker image
   - Restart containers với docker-compose
   - Health check

### 🔐 Required GitHub Secrets

Bạn cần thêm các secrets sau trong GitHub repository settings:

#### Navigation: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `DEV_SSH_PRIVATE_KEY` | SSH private key để connect vào dev server | `-----BEGIN OPENSSH PRIVATE KEY-----\n...` |
| `DEV_HOST` | IP hoặc domain của dev server | `192.168.1.100` hoặc `dev.yourdomain.com` |
| `DEV_USER` | Username SSH | `ubuntu` hoặc `root` |
| `DEV_PATH` | Đường dẫn project trên server | `/home/ubuntu/calmi-backend` |

### 📝 Setup Instructions

#### 1. Tạo SSH Key cho GitHub Actions

Trên máy local hoặc server:

```bash
# Tạo SSH key mới
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions_key

# Copy public key
cat ~/.ssh/github_actions_key.pub
```

**Trên Dev Server:**
```bash
# Thêm public key vào authorized_keys
echo "PUBLIC_KEY_CONTENT_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**Trên GitHub:**
- Copy **private key** (`~/.ssh/github_actions_key`)
- Thêm vào GitHub Secrets với tên `DEV_SSH_PRIVATE_KEY`

#### 2. Thêm GitHub Secrets

```bash
# Go to: https://github.com/YOUR_USERNAME/calmi-backend/settings/secrets/actions

# Thêm các secrets:
DEV_SSH_PRIVATE_KEY=<private_key_content>
DEV_HOST=<your_server_ip_or_domain>
DEV_USER=<ssh_username>
DEV_PATH=/home/ubuntu/calmi-backend
```

#### 3. Setup Development Server

**Cài đặt Docker và Docker Compose:**

```bash
# Update packages
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

**Clone repository trên server:**

```bash
cd ~
git clone https://github.com/vamcrizer/calmi-backend.git
cd calmi-backend

# Tạo .env file
cp .env.example .env
nano .env  # Edit với credentials thật
```

**Tạo .env file trên server:**

```bash
# Database
DATABASE_URL=postgresql://calmi_user:your_password@db:5432/calmi_db

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=["http://localhost:3000","https://yourdomain.com"]

# Email (nếu có)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### 4. Test Deployment Manually

```bash
# Trên dev server
cd ~/calmi-backend
docker-compose up -d --build

# Check logs
docker-compose logs -f

# Check health
curl http://localhost:8000/health
```

#### 5. Enable GitHub Actions

Workflow sẽ tự động chạy khi:
- Push code lên branch `main` hoặc `dev`
- Tạo Pull Request vào branch `main` hoặc `dev`

**Workflow triggers:**
- `main` branch → Deploy to dev automatically
- `dev` branch → Deploy to dev automatically
- Pull Request → Run tests only (no deployment)

### 🚀 Usage

**Deploy to Development:**

```bash
# Merge to main or dev branch
git checkout dev
git add .
git commit -m "feat: new feature"
git push origin dev

# GitHub Actions sẽ tự động:
# 1. Run linting
# 2. Run tests
# 3. Build Docker image
# 4. Deploy to dev server
# 5. Run health check
```

### 📊 Monitor Workflow

- Xem workflow runs: https://github.com/vamcrizer/calmi-backend/actions
- Mỗi workflow run sẽ hiển thị:
  - ✅ Success steps (màu xanh)
  - ❌ Failed steps (màu đỏ)
  - 📋 Logs chi tiết

### 🔧 Troubleshooting

**SSH Connection Failed:**
```bash
# Kiểm tra SSH key trên server
cat ~/.ssh/authorized_keys

# Kiểm tra SSH permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

**Docker Permission Denied:**
```bash
# Thêm user vào docker group
sudo usermod -aG docker $USER

# Logout và login lại
```

**Health Check Failed:**
```bash
# Kiểm tra container status
docker-compose ps

# Xem logs
docker-compose logs backend

# Kiểm tra port
curl http://localhost:8000/health
```

### 📦 GitHub Container Registry

Images được push lên: `ghcr.io/vamcrizer/calmi-backend`

**Pull image manually:**
```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull image
docker pull ghcr.io/vamcrizer/calmi-backend:main
```

### 🎯 Next Steps

1. ✅ Setup GitHub Secrets
2. ✅ Setup Dev Server
3. ✅ Test manual deployment
4. ✅ Push code to trigger workflow
5. ⬜ Setup staging environment (optional)
6. ⬜ Setup production environment (optional)
7. ⬜ Add Slack/Discord notifications (optional)

### 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [GHCR Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
