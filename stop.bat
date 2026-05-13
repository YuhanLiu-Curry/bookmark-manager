@echo off
taskkill /f /im python.exe 2>nul
echo 服务已停止
timeout /t 2 >nul
