#!/usr/bin/env bash
# Tạo app Backstage thật, nằm CẠNH repo labs này (không nằm trong nó).
# Chạy: bash scripts/setup-backstage.sh
set -e

echo "=== Kiểm tra yêu cầu ==="
command -v node >/dev/null 2>&1 || { echo "Chưa cài Node.js. Cài Node 20/22 LTS trước."; exit 1; }
command -v yarn >/dev/null 2>&1 || { echo "Chưa cài Yarn. Chạy: npm install -g yarn"; exit 1; }

NODE_VERSION=$(node -v)
echo "Node version: $NODE_VERSION (khuyến nghị 20.x hoặc 22.x LTS)"

echo ""
echo "=== Tạo Backstage app ==="
echo "Gợi ý đặt tên: ai-delivery-portal-app"
cd ..
npx @backstage/create-app@latest

echo ""
echo "=== Xong bước tạo app ==="
echo "Bước tiếp theo:"
echo "  1. cd <ten-app-vua-tao>"
echo "  2. Copy nội dung examples/app-config.local.yaml.snippet vào app-config.local.yaml"
echo "  3. yarn dev"
echo "  4. Mở http://localhost:3000"
