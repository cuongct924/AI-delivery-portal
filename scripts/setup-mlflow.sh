#!/usr/bin/env bash
# Dựng MLflow tracking server bằng Docker để làm backend mock cho
# Model Registry + Experiment Tracking.
set -e

command -v docker >/dev/null 2>&1 || { echo "Chưa cài Docker."; exit 1; }

CONTAINER_NAME="ai-delivery-portal-mlflow"

if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
  echo "Container $CONTAINER_NAME đã tồn tại, khởi động lại..."
  docker start $CONTAINER_NAME
else
  echo "Tạo mới container MLflow..."
  docker run -d \
    --name $CONTAINER_NAME \
    -p 5000:5000 \
    ghcr.io/mlflow/mlflow:latest \
    mlflow server --host 0.0.0.0 --port 5000
fi

echo ""
echo "=== MLflow đang chạy tại http://localhost:5000 ==="
echo ""
echo "Thử gọi API bằng curl:"
echo '  curl http://localhost:5000/api/2.0/mlflow/experiments/search -X POST \'
echo '    -H "Content-Type: application/json" -d "{}"'
echo ""
echo "Dừng container khi không dùng: docker stop $CONTAINER_NAME"
