import sys
import os

# 日志输出到文件，不弹窗口
log_path = os.path.join(os.path.dirname(__file__), 'app.log')
log = open(log_path, 'a', encoding='utf-8')
sys.stdout = log
sys.stderr = log

print('=== 收藏管理器启动 ===')

from app import app, init_db
init_db()
app.run(host='0.0.0.0', port=5000, debug=False)
