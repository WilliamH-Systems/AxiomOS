# Deploying AxiomOS Web Service to Render

This guide will help you deploy the AxiomOS web service to Render.com using the `web-service` branch.

## 🚀 Quick Deploy

### 1. Push the Web Service Branch

```bash
# Make sure you're on the web-service branch
git checkout web-service

# Push to GitHub
git push origin web-service
```

### 2. Deploy on Render

1. Go to [render.com](https://render.com) and sign up/in
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select the `web-service` branch
5. Render will auto-detect the Python configuration
6. Configure environment variables (see below)
7. Click "Deploy"

## ⚙️ Environment Variables

In your Render dashboard, configure these environment variables:

### Required
- `GROQ_API_KEY`: Your Groq API key from [groq.com](https://groq.com)

### Optional (but Recommended)
- `GROQ_MODEL`: `llama-3.1-8b-instant` (default)
- `GROQ_MAX_TOKENS`: `1000` (default)
- `GROQ_TEMPERATURE`: `0.7` (default)
- `LOG_LEVEL`: `INFO` (default)
- `CORS_ORIGINS`: `https://your-app-name.onrender.com` (for security)

### Database (Optional)
If you add PostgreSQL and Redis services on Render:

**PostgreSQL:**
- `DB_HOST`: Auto-provided by Render
- `DB_PORT`: `5432`
- `DB_NAME`: `axiomos`
- `DB_USER`: Auto-provided by Render
- `DB_PASSWORD`: Auto-provided by Render

**Redis:**
- `REDIS_HOST`: Auto-provided by Render
- `REDIS_PORT`: `6379`
- `REDIS_DB`: `0`
- `REDIS_PASSWORD`: Auto-provided by Render

## 📁 Project Structure

The web service includes:

```
/
├── static/
│   ├── index.html          # Main web interface
│   ├── css/
│   │   └── style.css       # Responsive styling
│   └── js/
│       └── app.js          # Chat functionality
├── fastapi_app.py          # Updated to serve frontend
├── src/                    # Core AxiomOS functionality
├── requirements.txt         # Dependencies for Render
├── render.yaml            # Render configuration
└── .env.production.example # Environment template
```

## 🌐 Features

The web service provides:

- **Modern Web Interface**: Clean, responsive chat UI
- **Real-time Streaming**: Token-by-token response streaming
- **Settings Panel**: Configure model parameters
- **Memory Management**: Session and long-term memory
- **Health Monitoring**: Built-in health checks
- **API Endpoints**: Full REST API available
- **Mobile Responsive**: Works on all devices

## 🛠️ Development vs Production

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python fastapi_app.py
# Visit http://localhost:8000
```

### Production on Render
- Automatically configured through `render.yaml`
- Uses production-grade settings
- Serves static files efficiently
- Health checks for monitoring

## 🔧 Configuration Options

### Model Settings
- `llama-3.1-8b-instant`: Fast, efficient
- `llama-3.2-3b-preview`: Smaller model
- `gemma2-9b-it`: Google model option

### Scaling
- **Starter Plan**: Good for testing and light use
- **Standard Plan**: Recommended for production
- Add Redis/PostgreSQL for persistent storage

## 🔍 API Endpoints

All original API endpoints are available:

- `GET /` - Web interface
- `GET /health` - Health status
- `POST /chat` - Non-streaming chat
- `POST /chat/stream` - Streaming chat
- `GET /config` - Current configuration
- Session and memory management endpoints

## 🚨 Troubleshooting

### Common Issues

1. **Build Fails**: Check `requirements.txt` matches dependencies
2. **404 Errors**: Ensure static files are included in git
3. **CORS Issues**: Set `CORS_ORIGINS` to your Render URL
4. **Database Errors**: PostgreSQL/Redis are optional, app will fallback
5. **Memory Issues**: Add Redis service for session persistence

### Logs and Monitoring

- Check Render logs for deployment issues
- Use `/health` endpoint to monitor status
- Monitor memory usage on Render dashboard

## 🔄 Updates and Maintenance

### Updating the App
```bash
# Make changes on web-service branch
git add .
git commit -m "Update web interface"
git push origin web-service
# Render will auto-deploy
```

### Database Migrations
- Schema changes require manual migration
- Backup data before major updates
- Test in staging first

## 💡 Tips

1. **Start Simple**: Deploy without databases first
2. **Monitor Usage**: Check Render metrics regularly
3. **Security**: Set specific CORS origins in production
4. **Backups**: Enable Render database backups if using PostgreSQL
5. **Performance**: Consider upgrading plans for higher traffic

## 📚 Documentation

- [Render Python Docs](https://render.com/docs/deploy-python-fastapi)
- [AxiomOS README](../main/README.md)
- [Groq API Docs](https://groq.com/docs/)

---

Your AxiomOS web service will be available at: `https://your-app-name.onrender.com`

🎉 **You're ready to deploy!**