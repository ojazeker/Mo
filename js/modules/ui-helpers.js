import { Mo } from './core.js';

Object.assign(Mo.prototype, {
    colorsFromManaCost(manaCost) {
        const order = ['W', 'U', 'B', 'R', 'G'];
        const found = new Set(manaCost.toUpperCase().match(/[WUBRG]/g) || []);
        return order.filter(c => found.has(c));
    },

    buildColorPips(colors) {
        if (!colors.length) return '';
        const colorMap = { W: 'w', U: 'u', B: 'b', R: 'r', G: 'g' };
        const pips = colors.map((color) => {
            const suffix = colorMap[color] || 'c';
            return `<span class="token-pip token-pip-${suffix}" title="${color}"></span>`;
        }).join('');
        return `<span class="token-pips">${pips}</span>`;
    },

    _showAvatarSection(inputId, cardId, avatarId) {
        document.getElementById(inputId).style.display = 'none';
        document.getElementById(cardId).style.display = 'none';
        document.getElementById(avatarId).style.display = 'block';
    },

    _hideAvatarSection(inputId, avatarId) {
        document.getElementById(avatarId).style.display = 'none';
        document.getElementById(inputId).style.display = 'block';
    },

    async _printAvatar(name, btnId) {
        const btn = document.getElementById(btnId);
        btn.disabled = true;
        btn.textContent = 'Printing...';
        try {
            await fetch(`/api/print/avatar?name=${encodeURIComponent(name)}`, { method: 'POST' });
        } catch (e) {
            console.error('Avatar print failed:', e);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Print';
        }
    },

    _showWindowSection(inputId, cardId, show) {
        document.getElementById(inputId).style.display = show ? 'none' : 'block';
        document.getElementById(cardId).style.display = show ? 'block' : 'none';
    },

    _displayCardInWindow(card, imgId, rulesId) {
        const img = document.getElementById(imgId);
        const rules = document.getElementById(rulesId);
        if (card.hasLocalImage && card.imageUrl) {
            img.src = card.imageUrl;
            img.alt = card.name || '';
            img.style.display = 'block';
        } else {
            img.removeAttribute('src');
            img.style.display = 'none';
        }
        rules.textContent = (card.text || '').trim() || (card.type || '') || 'No rules text.';
    },
});