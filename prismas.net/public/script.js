document.addEventListener('DOMContentLoaded', () => {
    loadAnnouncements();
    loadAppInfo();
    setupMobileNav();
    updateCopyrightYear();
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

        if (info.apkFilename) {
            const downloadLink = document.getElementById('download-link');
            if (downloadLink) downloadLink.href = `/apk/${encodeURIComponent(info.apkFilename)}`;
        }
    } catch (error) {
        // Varsayılan değerler kalır
        console.warn('Uygulama bilgileri yüklenemedi:', error);
    }
}

function setupMobileNav() {
    const toggle = document.getElementById('nav-toggle');
    const menu = document.getElementById('nav-menu');
    if (!toggle || !menu) return;

    toggle.addEventListener('click', () => {
        const isOpen = menu.classList.toggle('nav-open');
        toggle.setAttribute('aria-expanded', String(isOpen));
    });

    // Menü linklerine tıklayınca mobil menüyü kapat
    menu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            menu.classList.remove('nav-open');
            toggle.setAttribute('aria-expanded', 'false');
        });
    });
}

function updateCopyrightYear() {
    const yearEl = document.getElementById('copyright-year');
    if (yearEl) yearEl.textContent = String(new Date().getFullYear());
}
