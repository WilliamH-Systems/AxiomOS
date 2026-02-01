# Mandatory Services Setup for AxiomOS

## 🚨 **Important: PostgreSQL & Redis Are Required**

AxiomOS requires both PostgreSQL and Redis for full functionality. The previous deployment used fallbacks, but for production, these services are **mandatory**.

## 🏗️ **Updated Deployment Configuration**

### **New render.yaml Features:**

1. **PostgreSQL Database Service**
   ```yaml
   - type: postgres
     name: axiomos-db
     plan: starter
     databaseName: axiomos
     user: axiomos_user
   ```

2. **Redis Cache Service**
   ```yaml
   - type: redis
     name: axiomos-redis
     plan: starter
   ```

3. **Automatic Service Connection**
   - **Auto-connection**: Web service automatically connects to database/redis
   - **Environment variables**: Render automatically injects connection details
   - **No manual configuration needed**

## 🔧 **Deployment Steps**

### **1. Update Your Render Service**

Since your app is already deployed, you need to:

1. **Go to Render Dashboard**
2. **Delete current service** (to recreate with proper dependencies)
3. **Create new service** using updated `render.yaml`

### **2. Option A: Re-deploy with Updated Config**

```bash
# Ensure latest config is pushed
git push origin web-service

# In Render Dashboard:
# 1. Delete existing axiomos-web service
# 2. Click "New +"
# 3. Select "Web Service"
# 4. Connect repo and choose web-service branch
# 5. Render will read updated render.yaml and create all 3 services
```

### **3. Option B: Add Services Manually**

If you want to keep the existing web service:

1. **Add PostgreSQL**:
   - Render Dashboard → "New +" → "PostgreSQL"
   - Name: `axiomos-db`
   - Plan: Starter
   - Database name: `axiomos`

2. **Add Redis**:
   - Render Dashboard → "New +" → "Redis"
   - Name: `axiomos-redis`
   - Plan: Starter

3. **Connect Services**:
   - Go to your web service settings
   - Add environment variables manually
   - Use connection details from PostgreSQL/Redis services

## 📋 **Manual Environment Variables (Option B)**

### **PostgreSQL Connection:**
```bash
DB_HOST=your-postgres-host.render.com
DB_PORT=5432
DB_NAME=axiomos
DB_USER=your-postgres-user
DB_PASSWORD=your-postgres-password
```

### **Redis Connection:**
```bash
REDIS_HOST=your-redis-host.render.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-redis-password
```

## ✅ **Verification**

### **After Deployment, Check:**

1. **Health Endpoint**:
   ```bash
   curl https://your-app.onrender.com/health
   ```
   Should show:
   ```json
   {
     "status": "healthy",
     "database": true,
     "redis": true,
     "overall": "healthy"
   }
   ```

2. **App Logs**: Should show:
   ```bash
   ✅ Database tables initialized
   ✅ Redis connection successful
   🚀 AxiomOS API is ready!
   ```

## 🚨 **Current Status**

Your current deployment is **running but incomplete**:
- ✅ Web interface works
- ✅ Chat functionality works (in-memory)
- ❌ PostgreSQL not connected
- ❌ Redis not connected
- ❌ Session persistence not working
- ❌ Long-term memory not working

## 🎯 **Next Steps**

### **Immediate Action Required:**

1. **Redeploy** with the updated `render.yaml` (recommended)
2. **Or manually add** PostgreSQL and Redis services
3. **Set GROQ_API_KEY** in Render environment variables

### **After Fix:**
- ✅ Session persistence
- ✅ Long-term memory
- ✅ Multi-user support
- ✅ Data durability

---

## 🚀 **Why This Matters**

### **PostgreSQL Required For:**
- Long-term memory storage
- User preferences
- Conversation history persistence
- Multi-user data separation

### **Redis Required For:**
- Session management
- Real-time session data
- Performance optimization
- User state caching

### **Without These Services:**
- Data lost on restart
- No multi-user support
- Poor performance
- No memory persistence

---

**🎉 Fix this now to have a fully functional AxiomOS deployment!**