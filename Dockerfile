# 1. Official Python base image matching tested environment (Python 3.14, slim variant)
FROM python:3.14-slim

# 2. Environment variables for Python runtime and Streamlit configuration
# - PYTHONDONTWRITEBYTECODE: Disables writing .pyc files to keep image lightweight and avoid cache writes
# - PYTHONUNBUFFERED: Ensures standard output/error are sent directly to Cloud Run logs without buffering
# - PORT: Cloud Run default port fallback (Cloud Run injects PORT at container startup)
# - STREAMLIT_SERVER_PORT: Streamlit server listening port
# - STREAMLIT_SERVER_ADDRESS: Bind to 0.0.0.0 to accept traffic from Cloud Run load balancer
# - STREAMLIT_SERVER_HEADLESS: Run in headless mode without browser launch triggers
# - STREAMLIT_BROWSER_GATHER_USAGE_STATS: Disable Streamlit telemetry outbound network calls
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    STREAMLIT_SERVER_PORT=8080 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 3. Set the application working directory
WORKDIR /app

# 4. Copy dependency specification and install Python packages
# Layer caching optimization: install dependencies before copying application code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy application source code, template assets, and root modules
# Non-application files, dev caches, and secrets are excluded by .dockerignore
COPY . .

# 6. Expose default port (documentary; Cloud Run maps port dynamically)
EXPOSE 8080

# 7. Start Streamlit app with dynamic $PORT evaluation
CMD ["sh", "-c", "streamlit run src/review_ui/app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
