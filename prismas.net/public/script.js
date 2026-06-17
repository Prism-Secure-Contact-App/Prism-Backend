document.addEventListener('DOMContentLoaded', () => {
    loadAnnouncements();
    loadAppInfo();
});

async function loadAnnouncements() {
    const grid = document.getElementById('news-grid');
    if (!grid) return;

    try {
        const response = await fetch('/content/announcements.json');
        if (!response.ok) throw new Error('Duyurular yüklenemedi');
        const data = await response.json();

        const announcements = Array.isArray(data) ? data : data.announcements || [];

        grid.innerHTML = announcements.length
            ? announcements.map(item => createNewsCard(item)).join('')
            : '<p class="no-news">Henüz duyuru bulunmuyor.</p>';
    } catch (error) {
        console.warn('Duyurular yüklenemedi:', error);
        grid.innerHTML = '<p class="no-news">Duyurular geçici olarak kullanılamıyor.</p>';
    }
}

function createNewsCard(item) {
    const date = item.date
        ? new Date(item.date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' })
        : '';

    return `
        <article class="news-card">
            ${item.tag ? `<span class="news-tag">${escapeHtml(item.tag)}</span>` : ''}
            ${date ? `<div class="news-date">${date}</div>` : ''}
            <h3>${escapeHtml(item.title)}</h3>
            <p>${escapeHtml(item.summary)}</p>
        </article>
    `;
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function loadAppInfo() {
    try {
        const response = await fetch('/content/app-info.json');
        if (!response.ok) return;
        const info = await response.json();

        if (info.version) {
            const versionEl = document.getElementById('version');
            if (versionEl) versionEl.textContent = `v${info.version}`;
        }

        if (info.size && info.androidVersion) {
            const fileInfoEl = document.getElementById('file-info');
            if (fileInfoEl) fileInfoEl.textContent = `${info.size} · Android ${info.androidVersion}+`;
        }
    } catch (error) {
        // Varsayılan değerler kalır
    }
}
