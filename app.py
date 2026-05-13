import sqlite3
import os
import json
from datetime import datetime
from urllib.parse import urlparse
import re
from flask import Flask, request, jsonify, render_template, g

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        title TEXT DEFAULT '',
        source TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        category TEXT DEFAULT '默认',
        tags TEXT DEFAULT '',
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )''')
    # ensure default category exists
    conn.execute("INSERT OR IGNORE INTO categories (name) VALUES ('默认')")
    conn.commit()
    conn.close()


# ------- Bookmark APIs -------

@app.route('/bookmarklet')
def bookmarklet_page():
    return render_template('bookmarklet.html')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/bookmarks', methods=['GET'])
def list_bookmarks():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    tag = request.args.get('tag', '').strip()
    status = request.args.get('status', '').strip()  # unread / read

    db = get_db()
    sql = 'SELECT * FROM bookmarks WHERE 1=1'
    params = []

    if q:
        sql += ' AND (title LIKE ? OR url LIKE ? OR notes LIKE ? OR tags LIKE ?)'
        p = f'%{q}%'
        params.extend([p, p, p, p])
    if category:
        sql += ' AND category = ?'
        params.append(category)
    if tag:
        sql += ' AND tags LIKE ?'
        params.append(f'%{tag}%')
    if status == 'unread':
        sql += ' AND is_read = 0'
    elif status == 'read':
        sql += ' AND is_read = 1'

    sql += ' ORDER BY updated_at DESC'
    rows = db.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/bookmarks/<int:bid>', methods=['GET'])
def get_bookmark(bid):
    db = get_db()
    row = db.execute('SELECT * FROM bookmarks WHERE id = ?', (bid,)).fetchone()
    if not row:
        return jsonify({'error': 'not found'}), 404
    return jsonify(dict(row))


@app.route('/api/bookmarks', methods=['POST'])
def create_bookmark():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    title = data.get('title', '').strip()
    source = data.get('source', '').strip()
    notes = data.get('notes', '').strip()
    category = data.get('category', '').strip() or '默认'
    tags = data.get('tags', '').strip()
    # auto-detect source & tags from URL if not provided
    if not source or not tags:
        auto_src, auto_tag = parse_meta(url)
        if not source:
            source = auto_src
        if not tags:
            tags = auto_tag

    db = get_db()
    c = db.execute('''INSERT INTO bookmarks (url, title, source, notes, category, tags)
        VALUES (?, ?, ?, ?, ?, ?)''', (url, title, source, notes, category, tags))
    db.commit()
    row = db.execute('SELECT * FROM bookmarks WHERE id = ?', (c.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route('/api/bookmarks/<int:bid>', methods=['PUT'])
def update_bookmark(bid):
    data = request.json
    db = get_db()
    existing = db.execute('SELECT * FROM bookmarks WHERE id = ?', (bid,)).fetchone()
    if not existing:
        return jsonify({'error': 'not found'}), 404

    title = data.get('title', existing['title'])
    url = data.get('url', existing['url'])
    source = data.get('source', existing['source'])
    notes = data.get('notes', existing['notes'])
    category = data.get('category', existing['category'])
    tags = data.get('tags', existing['tags'])
    is_read = data.get('is_read', existing['is_read'])

    db.execute('''UPDATE bookmarks SET url=?, title=?, source=?, notes=?,
        category=?, tags=?, is_read=?, updated_at=datetime('now','localtime')
        WHERE id=?''', (url, title, source, notes, category, tags, is_read, bid))
    db.commit()
    row = db.execute('SELECT * FROM bookmarks WHERE id = ?', (bid,)).fetchone()
    return jsonify(dict(row))


@app.route('/api/bookmarks/<int:bid>', methods=['DELETE'])
def delete_bookmark(bid):
    db = get_db()
    db.execute('DELETE FROM bookmarks WHERE id = ?', (bid,))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/bookmarks/<int:bid>/toggle-read', methods=['POST'])
def toggle_read(bid):
    db = get_db()
    db.execute('''UPDATE bookmarks SET is_read = CASE WHEN is_read=0 THEN 1 ELSE 0 END,
        updated_at=datetime('now','localtime') WHERE id=?''', (bid,))
    db.commit()
    row = db.execute('SELECT is_read FROM bookmarks WHERE id = ?', (bid,)).fetchone()
    return jsonify({'is_read': row['is_read'] if row else 0})


# ------- Category APIs -------

@app.route('/api/categories', methods=['GET'])
def list_categories():
    db = get_db()
    rows = db.execute('SELECT c.*, (SELECT COUNT(*) FROM bookmarks b WHERE b.category = c.name) AS count FROM categories c ORDER BY c.id').fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/categories', methods=['POST'])
def create_category():
    name = request.json.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    db = get_db()
    try:
        db.execute('INSERT INTO categories (name) VALUES (?)', (name,))
        db.commit()
        row = db.execute('SELECT *, 0 AS count FROM categories WHERE name = ?', (name,)).fetchone()
        return jsonify(dict(row)), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': '分类已存在'}), 409


@app.route('/api/categories/<int:cid>', methods=['PUT'])
def rename_category(cid):
    name = request.json.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400
    db = get_db()
    old = db.execute('SELECT name FROM categories WHERE id = ?', (cid,)).fetchone()
    if not old:
        return jsonify({'error': 'not found'}), 404
    old_name = old['name']
    db.execute('UPDATE categories SET name = ? WHERE id = ?', (name, cid))
    db.execute('UPDATE bookmarks SET category = ? WHERE category = ?', (name, old_name))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/categories/<int:cid>', methods=['DELETE'])
def delete_category(cid):
    db = get_db()
    name_row = db.execute('SELECT name FROM categories WHERE id = ?', (cid,)).fetchone()
    if not name_row:
        return jsonify({'error': 'not found'}), 404
    db.execute('UPDATE bookmarks SET category = ? WHERE category = ?', ('默认', name_row['name']))
    db.execute('DELETE FROM categories WHERE id = ?', (cid,))
    db.commit()
    return jsonify({'ok': True})


# ------- Import / Export -------

@app.route('/api/export', methods=['GET'])
def export_bookmarks():
    db = get_db()
    rows = db.execute('SELECT * FROM bookmarks ORDER BY created_at DESC').fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/import', methods=['POST'])
def import_bookmarks():
    data = request.json
    if not isinstance(data, list):
        return jsonify({'error': '需要 JSON 数组'}), 400
    db = get_db()
    count = 0
    for item in data:
        url = item.get('url', '').strip()
        if not url:
            continue
        db.execute('''INSERT INTO bookmarks (url, title, source, notes, category, tags)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (url, item.get('title', ''), item.get('source', ''),
             item.get('notes', ''), item.get('category', '默认'), item.get('tags', '')))
        count += 1
    db.commit()
    return jsonify({'imported': count})


# ------- Utilities -------

SOURCE_MAP = {
    'mp.weixin.qq.com': ('公众号', '微信'),
    'zhihu.com': ('知乎', '知乎'),
    'zhuanlan.zhihu.com': ('知乎专栏', '知乎'),
    'github.com': ('GitHub', 'GitHub'),
    'gist.github.com': ('GitHub Gist', 'GitHub'),
    'juejin.cn': ('掘金', '掘金'),
    'segmentfault.com': ('SegmentFault', '技术'),
    'csdn.net': ('CSDN', '技术'),
    'bilibili.com': ('B站', '视频'),
    'douban.com': ('豆瓣', '豆瓣'),
    'weibo.com': ('微博', '微博'),
    'youtube.com': ('YouTube', '视频'),
    'medium.com': ('Medium', '英文'),
    'stackoverflow.com': ('StackOverflow', '技术'),
    'developer.mozilla.org': ('MDN', '技术'),
    'docs.python.org': ('Python文档', 'Python'),
    'arxiv.org': ('arXiv', '论文'),
    'sspai.com': ('少数派', '科技'),
    '36kr.com': ('36氪', '科技'),
    'huxiu.com': ('虎嗅', '科技'),
    'infoq.cn': ('InfoQ', '技术'),
    'news.ycombinator.com': ('Hacker News', '英文'),
    'reddit.com': ('Reddit', '英文'),
    'twitter.com': ('Twitter', '社交'),
    'x.com': ('X', '社交'),
    'v2ex.com': ('V2EX', '技术'),
    'ruanyifeng.com': ('阮一峰', '博客'),
}


def parse_meta(url):
    """Extract source name and suggested tags from URL domain."""
    host = urlparse(url).hostname or ''
    host = host.lower().removeprefix('www.')
    source = ''
    tags = ''
    for domain, (src, tag) in SOURCE_MAP.items():
        if host == domain or host.endswith('.' + domain):
            source = src
            tags = tag
            break
    if not source:
        parts = host.split('.')
        if len(parts) >= 2:
            source = parts[-2]  # the main domain name
    return source, tags


@app.route('/api/fetch-title', methods=['GET'])
def fetch_title():
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'title': ''})
    return jsonify({'title': _scrape_title(url)})


def _scrape_title(url):
    try:
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
        }
        resp = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
        html = resp.text

        # 1) <title> tag
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if m:
            title = re.sub(r'\s+', ' ', m.group(1).strip())
            if title:
                return title

        # 2) og:title
        m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # 3) twitter:title
        m = re.search(r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # 4) first <h1>
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
        if m:
            title = re.sub(r'<[^>]+>', '', m.group(1).strip())
            title = re.sub(r'\s+', ' ', title)
            if title:
                return title
    except Exception:
        pass
    return ''


@app.route('/api/fetch-meta', methods=['GET'])
def fetch_meta():
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'title': '', 'source': '', 'tags': ''})
    source, tags = parse_meta(url)
    title = _scrape_title(url)
    return jsonify({'title': title, 'source': source, 'tags': tags})


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
