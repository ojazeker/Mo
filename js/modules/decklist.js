import { Mo } from './core.js';

Object.assign(Mo.prototype, {
    setupDecklistListeners() {
        this.decklistCards = [];
        document.getElementById('decklistPreviewBtn').addEventListener('click', () => this.decklistPreview());
        document.getElementById('decklistBackBtn').addEventListener('click', () => this.decklistGoBack());
        document.getElementById('decklistPrintBtn').addEventListener('click', () => this.decklistPrint());
    },

    parseDecklistText(text) {
        const entries = [];
        let section = 'deck';
        for (const rawLine of text.split('\n')) {
            const line = rawLine.trim();
            if (!line) continue;
            const lower = line.toLowerCase();
            if (lower === 'deck' || lower === 'maindeck' || lower === 'main deck') { section = 'deck'; continue; }
            if (lower === 'sideboard' || lower === 'side' || lower === 'sb') { section = 'sideboard'; continue; }
            const match = line.match(/^(\d+)x?\s+(.+)$/);
            if (match) {
                entries.push({ quantity: parseInt(match[1], 10), name: match[2].trim(), section });
            }
        }
        return entries;
    },

    async decklistPreview() {
        const text = document.getElementById('decklistTextarea').value.trim();
        const errorDiv = document.getElementById('decklistInputError');
        errorDiv.style.display = 'none';
        const entries = this.parseDecklistText(text);
        if (!entries.length) {
            errorDiv.textContent = 'No cards found. Paste a list like "4 Counterspell".';
            errorDiv.style.display = 'block';
            return;
        }
        document.getElementById('decklistInputSection').style.display = 'none';
        document.getElementById('decklistLoadingState').style.display = 'flex';
        try {
            const names = entries.map(e => e.name);
            const resp = await fetch('/api/decklist/lookup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ names }),
            });
            const data = await resp.json();
            const results = data.results || [];
            this.decklistCards = entries.map((entry, i) => ({ ...entry, ...(results[i] || {}) }));
            document.getElementById('decklistLoadingState').style.display = 'none';
            this._renderDecklistPreview(this.decklistCards);
            document.getElementById('decklistPreviewSection').style.display = 'block';
            const win = document.querySelector('.decklist-window');
            if (win) {
                const top = win.getBoundingClientRect().top + window.scrollY - 8;
                window.scrollTo({ top, behavior: 'smooth' });
            }
        } catch (e) {
            console.error('Decklist lookup failed:', e);
            document.getElementById('decklistLoadingState').style.display = 'none';
            document.getElementById('decklistInputSection').style.display = 'block';
            errorDiv.textContent = 'Lookup failed. Is the server running?';
            errorDiv.style.display = 'block';
        }
    },

    _renderDecklistPreview(cards) {
        const container = document.getElementById('decklistCards');
        container.innerHTML = '';
        const found = cards.filter(c => c.found).length;
        document.getElementById('decklistStatus').textContent = `${found} of ${cards.length} cards found locally.`;
        let lastSection = null;
        cards.forEach((card, index) => {
            if (card.section !== lastSection) {
                lastSection = card.section;
                const label = document.createElement('div');
                label.className = 'decklist-section-label';
                label.textContent = card.section === 'sideboard' ? 'Sideboard' : 'Deck';
                container.appendChild(label);
            }
            const entry = document.createElement('div');
            entry.className = 'decklist-card-entry' + (card.found ? '' : ' not-found');
            const removeBtn = document.createElement('button');
            removeBtn.className = 'decklist-card-remove';
            removeBtn.textContent = '×';
            removeBtn.addEventListener('click', () => {
                this.decklistCards.splice(index, 1);
                this._renderDecklistPreview(this.decklistCards);
            });
            entry.appendChild(removeBtn);
            if (card.found && card.imageUrl) {
                const img = document.createElement('img');
                img.src = card.imageUrl;
                img.alt = card.name;
                entry.appendChild(img);
            } else {
                const placeholder = document.createElement('div');
                placeholder.className = 'decklist-card-not-found';
                placeholder.textContent = card.name + ' (not found)';
                entry.appendChild(placeholder);
            }
            const nameBar = document.createElement('div');
            nameBar.className = 'decklist-card-label';
            nameBar.textContent = `${card.quantity}x - ${card.name}`;
            entry.appendChild(nameBar);
            container.appendChild(entry);
        });
    },

    decklistGoBack() {
        document.getElementById('decklistPreviewSection').style.display = 'none';
        document.getElementById('decklistInputSection').style.display = 'block';
        document.getElementById('decklistInputError').style.display = 'none';
    },

    async decklistPrint() {
        const printable = this.decklistCards.filter(c => c.found && c.card_type);
        if (!printable.length) return;
        const btn = document.getElementById('decklistPrintBtn');
        btn.disabled = true;
        btn.textContent = 'Printing...';
        try {
            const payload = printable.map(c => ({
                card_type: c.card_type,
                cmc: c.cmc,
                filename: c.filename,
                quantity: c.quantity,
            }));
            await fetch('/api/decklist/print', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cards: payload }),
            });
        } catch (e) {
            console.error('Decklist print failed:', e);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Print All';
        }
    },
});
