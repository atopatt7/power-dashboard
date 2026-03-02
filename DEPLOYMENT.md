# 部署指南

## 🚀 快速開始（本地）

### 前置需求
- Python 3.8+
- Git

### 1. 克隆仓库
```bash
git clone https://github.com/YOUR_USERNAME/power-dashboard.git
cd power-dashboard
```

### 2. 启动后端
```bash
cd backend
python3 main.py
```

### 3. 访问仪表板
打开浏览器访问：`http://localhost:8000`

---

## ☁️ 部署到云端

### 选项 1: Heroku（推荐新手）

#### 前置条件
- Heroku 账户（https://www.heroku.com）
- Heroku CLI（https://devcenter.heroku.com/articles/heroku-cli）
- GitHub 账户

#### 步骤
```bash
# 1. 登录 Heroku
heroku login

# 2. 创建 Heroku 应用
heroku create your-app-name

# 3. 设置 Procfile（已包含在项目中）
# 推送代码
git push heroku main

# 4. 查看日志
heroku logs --tail
```

#### 创建 Procfile
在项目根目录创建 `Procfile`：
```
web: cd backend && python3 main.py
```

### 选项 2: Google Cloud Run（无服务器）

#### 步骤
```bash
# 1. 安装 Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# 2. 认证
gcloud auth login

# 3. 创建 Dockerfile（见下方）

# 4. 部署
gcloud run deploy power-dashboard \
  --source . \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated
```

#### Dockerfile
在项目根目录创建 `Dockerfile`：
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY backend/ backend/
COPY frontend/ frontend/

EXPOSE 8080

ENV PORT=8080

CMD cd backend && python3 main.py --port $PORT
```

### 选项 3: AWS Lightsail（虚拟机）

#### 步骤
1. 创建 Ubuntu 实例
2. SSH 连接到实例
3. 克隆 GitHub 仓库
4. 启动后端：`python3 backend/main.py`
5. 使用 Nginx 作为反向代理（可选）

---

## 🔧 环境变量配置

创建 `.env` 文件（仅本地使用）：
```
PORT=8000
HOST=0.0.0.0
DEBUG=false
```

**重要**：不要提交 `.env` 文件到 GitHub，已在 `.gitignore` 中排除。

---

## 📊 持久化数据

### 本地运行
- 数据库自动保存为 `backend/power_data.db`
- 配置保存为 `backend/powerbi_config.json`

### 云端运行
**注意**：云平台（Heroku、Cloud Run）通常是临时文件系统。建议：

1. **使用云存储**：
   - AWS S3
   - Google Cloud Storage
   - Heroku Postgres（数据库）

2. **简单方案**：接受数据丢失（演示用途）

---

## 🔐 生产环境注意事项

1. **改更后端端口**：
   ```python
   # backend/config.py
   PORT = int(os.getenv('PORT', 8000))
   ```

2. **禁用 Mock 数据**：
   - 创建 `backend/powerbi_config.json`
   - 配置真实 Power BI 连接

3. **HTTPS/SSL**：
   - 使用云平台自带的 SSL
   - 或使用 Cloudflare 免费 HTTPS

4. **监控和日志**：
   - 启用云平台的日志服务
   - 定期检查 `/tmp/dashboard.log`

---

## 📝 后续维护

### 更新代码
```bash
git add .
git commit -m "更新说明"
git push origin main

# 如果已部署到 Heroku
git push heroku main
```

### 数据库备份
```bash
# 本地备份
cp backend/power_data.db backup/power_data_$(date +%Y%m%d).db
```

---

## 🆘 故障排除

### 常见问题

**Q: 云端无法连接到后端**
- A: 检查防火墙规则，确保端口 8000/8080 开放

**Q: 数据库文件丢失**
- A: 这是云平台的预期行为，使用持久化存储（S3、PostgreSQL）

**Q: 时间显示错误**
- A: 确保云实例的时区设置为 UTC，前端会自动转换为台湾时间

---

## 📚 更多资源

- [Heroku 部署指南](https://devcenter.heroku.com)
- [Google Cloud Run 文档](https://cloud.google.com/run/docs)
- [AWS Lightsail 入门](https://lightsail.aws.amazon.com)
