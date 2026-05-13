# Bookmark Manager

本地书签管理工具，Flask + SQLite，支持一键收藏、自动识别来源标签。

## 启动

```bash
pip install -r requirements.txt
python run.py
```

浏览器访问 http://localhost:5000

## 功能

- **书签管理** — 增删改查、分类、标签、已读/未读
- **自动识别** — 粘贴 URL 自动抓取标题、识别来源（公众号/知乎/GitHub 等 25+ 站点）、建议标签
- **一键收藏** — 浏览器小书签，浏览任意页面点一下即存
- **搜索筛选** — 全文搜索、按分类/标签/未读状态筛选
- **导入导出** — JSON 格式备份恢复

## 一键收藏小书签

打开 http://localhost:5000/bookmarklet ，拖拽按钮到浏览器书签栏即可。

## 技术栈

- Python Flask
- SQLite (WAL mode)
- Vanilla HTML/CSS/JS
