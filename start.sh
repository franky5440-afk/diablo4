#!/bin/bash
cd "$(dirname "$0")"
mkdir -p logs data
./venv/bin/python build_site.py
nohup ./venv/bin/python app.py > logs/server.log 2>&1 &
sleep 2
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8768/ | grep -q 200; then
  echo "網站已啟動：http://127.0.0.1:8768"
else
  echo "啟動失敗，請查看 logs/server.log"
fi
