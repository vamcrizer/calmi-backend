# Deployment Workflow - Simplified Version

## Tổng quan thay đổi

Workflow deployment đã được đơn giản hóa theo yêu cầu để:

1. ✅ **Zip toàn bộ dự án** - Tạo file backend-deploy.zip
2. ✅ **Xóa toàn bộ thư mục dự án trên server** - Đảm bảo deployment sạch
3. ✅ **Giải nén dự án mới** - Unzip file vào thư mục dự án
4. ✅ **Copy .env từ thư mục mẹ** - Tự động copy .env từ parent directory
5. ✅ **Build Docker image và chạy container** - Sử dụng docker-compose
6. ✅ **Loại bỏ kiểm tra code quality** - Không chạy linting
7. ✅ **Loại bỏ chạy tests** - Không chạy pytest
8. ✅ **Cập nhật .dockerignore** - Cho phép .env khi build image

## File đã thay đổi

### 1. `.dockerignore`
```diff
# Environment files
-.env
-.env.*
-!.env.example
+# .env
+# .env.*
+# !.env.example
```
**Lý do:** Cho phép file `.env` được đưa vào Docker image khi build

### 2. `workflows/deploy.yml`

**Thay đổi chính:**
- ❌ Xóa job `test` (đã loại bỏ linting và testing)
- ✅ Đơn giản hóa thành 1 job duy nhất: `deploy-dev`
- ✅ Thêm bước tạo file zip
- ✅ Upload file zip lên server
- ✅ Xóa toàn bộ thư mục cũ trên server
- ✅ Giải nén file zip
- ✅ Tự động copy .env từ parent directory
- ✅ Build và chạy Docker containers

## Quy trình deployment mới

### Bước 1: Tạo deployment package
```bash
zip -r backend-deploy.zip . -x '*.git*' -x 'storage/*'
```

### Bước 2: Upload lên server
```bash
scp backend-deploy.zip $DEV_USER@$DEV_HOST:/tmp/
```

### Bước 3: Deploy trên server
```bash
# Backup .env từ parent directory hoặc project directory
cp $PARENT_DIR/.env /tmp/backup.env

# Stop containers hiện tại
docker-compose down

# Xóa thư mục dự án cũ
rm -rf $PROJECT_DIR

# Giải nén dự án mới
mkdir -p $PROJECT_DIR
unzip /tmp/backend-deploy.zip -d $PROJECT_DIR

# Copy .env vào thư mục dự án
cp /tmp/backup.env $PROJECT_DIR/.env

# Build và chạy containers mới
docker-compose up -d --build
```

### Bước 4: Health check
```bash
curl -f http://$DEV_HOST:8000/health
```

## Trigger workflow

Workflow sẽ tự động chạy khi:
- ✅ Push code lên branch `main`
- ✅ Push code lên branch `dev`
- ✅ Manual trigger qua GitHub Actions UI (workflow_dispatch)

## GitHub Secrets cần thiết

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `DEV_SSH_PRIVATE_KEY` | SSH private key | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DEV_HOST` | Server IP/domain | `192.168.1.100` hoặc `dev.yourdomain.com` |
| `DEV_USER` | SSH username | `ubuntu` hoặc `root` |
| `DEV_PATH` | Đường dẫn project trên server | `/home/ubuntu/calmi-backend` |

## Lưu ý quan trọng

### 1. File .env
- Workflow sẽ tự động tìm file `.env` từ:
  1. Thư mục mẹ của dự án (`$PARENT_DIR/.env`)
  2. Thư mục dự án hiện tại (`$PROJECT_DIR/.env`)
  3. Nếu không tìm thấy, sẽ copy từ `.env.example`

### 2. Docker image
- File `.env` giờ đây sẽ được đưa vào Docker image (do đã comment out trong `.dockerignore`)
- Điều này giúp container có thể sử dụng biến môi trường từ `.env`

### 3. Clean deployment
- Toàn bộ thư mục dự án cũ sẽ được XÓA HOÀN TOÀN
- Đảm bảo không có file rác từ deployment trước
- Containers cũ sẽ được stop và remove

### 4. Backup
- `.env` được backup tạm thời vào `/tmp/backup.env`
- Sau khi deploy xong, file backup sẽ được xóa

## So sánh với workflow cũ

| Feature | Workflow cũ | Workflow mới |
|---------|-------------|--------------|
| Code linting | ✅ Có | ❌ Đã loại bỏ |
| Run tests | ✅ Có | ❌ Đã loại bỏ |
| Git pull | ✅ Dùng git pull | ❌ Dùng zip/unzip |
| Xóa thư mục cũ | ❌ Không | ✅ Có |
| Copy .env | ❌ Thủ công | ✅ Tự động |
| .env trong image | ❌ Không | ✅ Có |
| Deployment steps | 2 jobs | 1 job |

## Cách sử dụng

### Deploy tự động
```bash
git add .
git commit -m "feat: new feature"
git push origin dev
```

### Deploy thủ công
1. Vào repository trên GitHub
2. Click tab "Actions"
3. Chọn workflow "Deploy to Development"
4. Click "Run workflow"
5. Chọn branch và click "Run workflow"

## Troubleshooting

### Deployment thất bại
```bash
# SSH vào server
ssh $DEV_USER@$DEV_HOST

# Kiểm tra logs
cd $DEV_PATH
docker-compose logs -f

# Kiểm tra containers
docker-compose ps
```

### .env không được copy
```bash
# Kiểm tra .env ở parent directory
ls -la $(dirname $DEV_PATH)/.env

# Copy thủ công nếu cần
cp $(dirname $DEV_PATH)/.env $DEV_PATH/.env
```

### Container không chạy
```bash
# Rebuild containers
cd $DEV_PATH
docker-compose down
docker-compose up -d --build

# Xem logs chi tiết
docker-compose logs backend
```

## Best Practices

1. **Backup .env trước khi deploy**
   ```bash
   # Trên server, backup .env vào thư mục mẹ
   cp ~/calmi-backend/.env ~/.env
   ```

2. **Test deployment locally trước**
   ```bash
   # Test trên local
   zip -r backend-deploy.zip . -x '*.git*' -x 'storage/*'
   unzip -l backend-deploy.zip  # Kiểm tra nội dung
   ```

3. **Monitor logs sau khi deploy**
   ```bash
   # Xem logs real-time
   ssh $DEV_USER@$DEV_HOST "cd $DEV_PATH && docker-compose logs -f"
   ```

## Kết luận

Workflow mới đã được tối ưu hóa để:
- ⚡ Deploy nhanh hơn (không chạy tests)
- 🧹 Clean deployment (xóa thư mục cũ)
- 🔒 Tự động quản lý .env
- 🐳 Đơn giản hóa quy trình Docker build
