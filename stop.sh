#!/bin/bash
pkill -f "python app.py" 2>/dev/null && echo "已停止" || echo "沒有執行中的伺服器"
