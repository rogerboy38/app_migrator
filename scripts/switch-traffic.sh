# Traffic Switching Script for Blue-Green Deployment
#!/bin/bash
# Usage: ./scripts/switch-traffic.sh [blue|green]

set -e

TARGET="${1:-green}"
NGINX_CONF="/etc/nginx/conf.d/frappe-upstream.conf"

echo "===== Switching traffic to $TARGET environment ====="

case "$TARGET" in
  blue)
    UPSTREAM_BACKEND="backend:8000"
    FRONTEND_PORT=80
    ;;
  green)
    UPSTREAM_BACKEND="backend-green:8000"
    FRONTEND_PORT=8081
    ;;
  *)
    echo "Invalid target: $TARGET"
    echo "Usage: $0 [blue|green]"
    exit 1
    ;;
esac

# Create nginx upstream configuration
cat > /tmp/frappe-upstream.conf << EOF
upstream frappe_backend {
    server $UPSTREAM_BACKEND;
}

server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://frappe_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }
    
    location /socket.io {
        proxy_pass http://frappe_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Origin "";
    }
}
EOF

# Apply nginx configuration
if [ -f "$NGINX_CONF" ]; then
    cp "$NGINX_CONF" "${NGINX_CONF}.backup.$(date +%s)"
fi

cat /tmp/frappe-upstream.conf > "$NGINX_CONF"

# Test and reload nginx
nginx -t && nginx -s reload || echo "Nginx reload attempted"

echo "===== Traffic switched to $TARGET ====="