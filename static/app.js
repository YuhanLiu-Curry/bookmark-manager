// ---- State ----
let currentFilter = { q: '', category: '', tag: '', status: '' };
let allTags = [];
let debounceTimer = null;

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
    loadCategories();
    loadBookmarks();
});

// ---- Sidebar ----
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// ---- Load categories ----
async function loadCategories() {
    const resp = await fetch('/api/categories');
    const cats = await resp.json();
    const ul = document.getElementById('categoryList');
    ul.innerHTML = cats.map(c => {
        const active = currentFilter.category === c.name ? 'active' : '';
        return `<li class="category-item ${active}" onclick="filterByCategory('${escHtml(c.name)}')">
            <span>${escHtml(c.name)}</span>
            <span class="count">${c.count}</span>
            <span class="cat-actions">
                <button onclick="event.stopPropagation(); showRenameCategory(${c.id},'${escHtml(c.name)}')" title="重命名">✎</button>
                ${c.name !== '默认' ? `<button onclick="event.stopPropagation(); deleteCategory(${c.id})" title="删除">✕</button>` : ''}
            </span>
        </li>`;
    }).join('');
    loadTags();
}

// ---- Load tags ----
async function loadTags() {
    const resp = await fetch('/api/bookmarks');
    const books = await resp.json();
    const tagSet = new Set();
    books.forEach(b => {
        (b.tags || '').split(',').map(t => t.trim()).filter(t => t).forEach(t => tagSet.add(t));
    });
    allTags = Array.from(tagSet).sort();
    const container = document.getElementById('tagList');
    if (allTags.length === 0) {
        container.innerHTML = '<span style="font-size:12px;color:var(--text-secondary)">暂无标签</span>';
        return;
    }
    container.innerHTML = allTags.map(t => {
        const active = currentFilter.tag === t ? 'active' : '';
        return `<span class="tag-chip ${active}" onclick="filterByTag('${escHtml(t)}')">${escHtml(t)}</span>`;
    }).join('');
}

// ---- Load bookmarks ----
async function loadBookmarks() {
    const params = new URLSearchParams();
    if (currentFilter.q) params.set('q', currentFilter.q);
    if (currentFilter.category) params.set('category', currentFilter.category);
    if (currentFilter.tag) params.set('tag', currentFilter.tag);
    if (currentFilter.status) params.set('status', currentFilter.status);

    const resp = await fetch('/api/bookmarks?' + params.toString());
    const books = await resp.json();

    const container = document.getElementById('bookmarkList');
    const emptyState = document.getElementById('emptyState');

    // stats
    document.getElementById('statsTotal').textContent = `${books.length} 条收藏`;
    const unreadCount = books.filter(b => b.is_read === 0).length;
    document.getElementById('statsUnread').textContent = unreadCount > 0 ? `未读 ${unreadCount}` : '';

    if (books.length === 0) {
        container.innerHTML = `<div class="empty-state"><p>没有匹配的收藏</p></div>`;
        return;
    }

    container.innerHTML = books.map(b => {
        const unreadClass = b.is_read === 0 ? 'unread' : '';
        const readIcon = b.is_read === 1 ? '◉' : '○';
        const readClass = b.is_read === 1 ? 'read' : '';
        const tags = (b.tags || '').split(',').map(t => t.trim()).filter(t => t);
        const tagsHtml = tags.length > 0
            ? `<div class="bookmark-tags">${tags.map(t => `<span class="tag" onclick="filterByTag('${escHtml(t)}')">${escHtml(t)}</span>`).join('')}</div>`
            : '';
        const notesHtml = b.notes ? `<div class="bookmark-notes">${escHtml(b.notes)}</div>` : '';
        const sourceHtml = b.source ? `<span class="source">${escHtml(b.source)}</span>` : '';

        return `<div class="bookmark-card ${unreadClass}">
            <div class="bookmark-info">
                <a class="bookmark-title" href="${escHtml(b.url)}" target="_blank" rel="noopener">${escHtml(b.title || b.url)}</a>
                <div class="bookmark-meta">
                    ${sourceHtml}
                    <span class="cat" onclick="filterByCategory('${escHtml(b.category)}')">${escHtml(b.category)}</span>
                    <span>${b.created_at}</span>
                </div>
                ${tagsHtml}
                ${notesHtml}
            </div>
            <div class="bookmark-actions">
                <button class="btn-read ${readClass}" onclick="toggleRead(${b.id})" title="切换已读">${readIcon}</button>
                <button onclick="showEditBookmark(${b.id})" title="编辑">✎</button>
                <button onclick="deleteBookmark(${b.id})" title="删除">✕</button>
            </div>
        </div>`;
    }).join('');
}

// ---- Filter helpers ----
function filterByCategory(name) {
    if (currentFilter.category === name) {
        currentFilter.category = '';
    } else {
        currentFilter.category = name;
        currentFilter.tag = '';
    }
    updateFilterBar();
    loadCategories();
    loadBookmarks();
}

function filterByTag(tag) {
    if (currentFilter.tag === tag) {
        currentFilter.tag = '';
    } else {
        currentFilter.tag = tag;
        currentFilter.category = '';
    }
    updateFilterBar();
    loadCategories();
    loadBookmarks();
}

function toggleAllUnread() {
    currentFilter.status = currentFilter.status === 'unread' ? '' : 'unread';
    updateFilterBar();
    loadBookmarks();
}

function updateFilterBar() {
    const bar = document.getElementById('filterBar');
    const label = document.getElementById('filterLabel');
    const parts = [];
    if (currentFilter.category) parts.push(`分类: ${currentFilter.category}`);
    if (currentFilter.tag) parts.push(`标签: ${currentFilter.tag}`);
    if (currentFilter.status === 'unread') parts.push('未读');
    if (parts.length > 0) {
        bar.classList.remove('hidden');
        label.textContent = parts.join(' | ');
    } else {
        bar.classList.add('hidden');
    }
}

function clearFilters() {
    currentFilter.category = '';
    currentFilter.tag = '';
    currentFilter.status = '';
    updateFilterBar();
    loadCategories();
    loadBookmarks();
}

// ---- Search ----
function debouncedSearch() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(doSearch, 300);
}

function doSearch() {
    const q = document.getElementById('searchInput').value.trim();
    currentFilter.q = q;
    document.getElementById('clearBtn').classList.toggle('hidden', !q);
    loadBookmarks();
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    document.getElementById('clearBtn').classList.add('hidden');
    currentFilter.q = '';
    loadBookmarks();
}

// ---- Toggle read ----
async function toggleRead(id) {
    await fetch(`/api/bookmarks/${id}/toggle-read`, { method: 'POST' });
    loadBookmarks();
}

// ---- Delete ----
async function deleteBookmark(id) {
    if (!confirm('确定删除这条收藏？')) return;
    await fetch(`/api/bookmarks/${id}`, { method: 'DELETE' });
    loadCategories();
    loadBookmarks();
}

// ---- Add / Edit Modal ----
function showAddBookmark() {
    document.getElementById('modalTitle').textContent = '添加收藏';
    document.getElementById('bookmarkForm').reset();
    document.getElementById('editId').value = '';
    populateCategorySelect();
    document.getElementById('modal').classList.remove('hidden');
}

async function showEditBookmark(id) {
    const resp = await fetch(`/api/bookmarks/${id}`);
    const b = await resp.json();
    document.getElementById('modalTitle').textContent = '编辑收藏';
    document.getElementById('editId').value = b.id;
    document.getElementById('inputUrl').value = b.url;
    document.getElementById('inputTitle').value = b.title;
    document.getElementById('inputSource').value = b.source;
    document.getElementById('inputNotes').value = b.notes;
    document.getElementById('inputTags').value = b.tags;
    populateCategorySelect(b.category);
    document.getElementById('modal').classList.remove('hidden');
}

function populateCategorySelect(selected) {
    const sel = document.getElementById('inputCategory');
    sel.innerHTML = '';
    // fetch categories
    fetch('/api/categories').then(r => r.json()).then(cats => {
        cats.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.name;
            opt.textContent = c.name;
            if (c.name === selected) opt.selected = true;
            sel.appendChild(opt);
        });
    });
}

function closeModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('modal').classList.add('hidden');
}

async function saveBookmark(e) {
    e.preventDefault();
    const id = document.getElementById('editId').value;
    const data = {
        url: document.getElementById('inputUrl').value.trim(),
        title: document.getElementById('inputTitle').value.trim(),
        source: document.getElementById('inputSource').value.trim(),
        notes: document.getElementById('inputNotes').value.trim(),
        category: document.getElementById('inputCategory').value,
        tags: document.getElementById('inputTags').value.trim(),
    };

    const url = id ? `/api/bookmarks/${id}` : '/api/bookmarks';
    const method = id ? 'PUT' : 'POST';
    await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    closeModal();
    loadCategories();
    loadBookmarks();
}

// ---- Auto fetch meta ----
async function autoFetchMeta() {
    const url = document.getElementById('inputUrl').value.trim();
    if (!url) return;
    const titleInput = document.getElementById('inputTitle');
    const sourceInput = document.getElementById('inputSource');
    const tagsInput = document.getElementById('inputTags');
    // skip if all fields already filled
    if (titleInput.value && sourceInput.value && tagsInput.value) return;
    const resp = await fetch('/api/fetch-meta?url=' + encodeURIComponent(url));
    const data = await resp.json();
    if (data.title && !titleInput.value) titleInput.value = data.title;
    if (data.source && !sourceInput.value) sourceInput.value = data.source;
    if (data.tags && !tagsInput.value) tagsInput.value = data.tags;
}

// ---- Category management ----
function showAddCategory() {
    document.getElementById('catModalTitle').textContent = '新建分类';
    document.getElementById('editCatId').value = '';
    document.getElementById('inputCatName').value = '';
    document.getElementById('catModal').classList.remove('hidden');
}

function showRenameCategory(id, name) {
    document.getElementById('catModalTitle').textContent = '重命名分类';
    document.getElementById('editCatId').value = id;
    document.getElementById('inputCatName').value = name;
    document.getElementById('catModal').classList.remove('hidden');
}

function closeCatModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('catModal').classList.add('hidden');
}

async function saveCategory(e) {
    e.preventDefault();
    const id = document.getElementById('editCatId').value;
    const name = document.getElementById('inputCatName').value.trim();
    if (!name) return;

    if (id) {
        await fetch(`/api/categories/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
    } else {
        await fetch('/api/categories', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
    }
    closeCatModal();
    loadCategories();
}

async function deleteCategory(id) {
    if (!confirm('确定删除此分类？已有收藏将移入「默认」分类。')) return;
    await fetch(`/api/categories/${id}`, { method: 'DELETE' });
    if (currentFilter.category) {
        // check if the deleted category was active
        const resp = await fetch('/api/categories');
        const cats = await resp.json();
        if (!cats.some(c => c.name === currentFilter.category)) {
            currentFilter.category = '';
            updateFilterBar();
        }
    }
    loadCategories();
    loadBookmarks();
}

// ---- Import / Export ----
async function exportData() {
    const resp = await fetch('/api/export');
    const data = await resp.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bookmarks-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

async function importData(event) {
    const file = event.target.files[0];
    if (!file) return;
    const text = await file.text();
    try {
        const data = JSON.parse(text);
        const resp = await fetch('/api/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        const result = await resp.json();
        alert(`导入完成，共 ${result.imported} 条`);
        loadCategories();
        loadBookmarks();
    } catch (e) {
        alert('导入失败，请检查 JSON 格式');
    }
    event.target.value = '';
}

// ---- Utility ----
function escHtml(s) {
    if (!s) return '';
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}
