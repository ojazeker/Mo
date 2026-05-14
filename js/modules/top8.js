import { Mo } from './core.js';

Object.assign(Mo.prototype, {
    setupTop8Listeners() {
        this._top8Index = null;

        const select = document.getElementById('top8FormatSelect');
        if (!select) return;

        select.addEventListener('change', () => this._top8LoadFormat(select.value));
        this._top8Init();
    },

    async _top8Init() {
        try {
            const resp = await fetch('/api/top8/index');
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            this._top8Index = await resp.json();
            const select = document.getElementById('top8FormatSelect');
            this._top8LoadFormat(select ? select.value : 'premodern');
        } catch (e) {
            this._top8ShowError('Could not load deck index. Run the build script first.');
        }
    },

    _top8LoadFormat(format) {
        const list = document.getElementById('top8DeckList');
        const errorDiv = document.getElementById('top8Error');
        errorDiv.style.display = 'none';

        if (!this._top8Index) {
            list.innerHTML = '<p class="top8-empty">No data available.</p>';
            return;
        }

        const decks = this._top8Index[format] || [];
        if (!decks.length) {
            list.innerHTML = '<p class="top8-empty">No decks found for this format.</p>';
            return;
        }

        list.innerHTML = '';
        decks.forEach((deck) => {
            const btn = document.createElement('button');
            btn.className = 'top8-deck-btn';
            btn.textContent = deck.name;
            btn.addEventListener('click', () => this._top8LoadDeck(format, deck.file, deck.name));
            list.appendChild(btn);
        });
    },

    async _top8LoadDeck(format, file, name) {
        const errorDiv = document.getElementById('top8Error');
        errorDiv.style.display = 'none';

        // Mark active
        document.querySelectorAll('.top8-deck-btn').forEach(b => b.classList.remove('active'));
        const clickedBtn = [...document.querySelectorAll('.top8-deck-btn')]
            .find(b => b.textContent === name);
        if (clickedBtn) clickedBtn.classList.add('active');

        try {
            const resp = await fetch(`/api/top8/${encodeURIComponent(format)}/${encodeURIComponent(file)}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const text = await resp.text();

            // Stuff the decklist into the textarea and trigger preview
            const textarea = document.getElementById('decklistTextarea');
            if (textarea) {
                textarea.value = text;
            }

            // Reset decklist to input state so Preview triggers cleanly
            const previewSection = document.getElementById('decklistPreviewSection');
            const inputSection   = document.getElementById('decklistInputSection');
            if (previewSection) previewSection.style.display = 'none';
            if (inputSection)   inputSection.style.display   = 'block';

            // Scroll the deck-row container horizontally to show the decklist window
            const decklistWin = document.querySelector('.decklist-window');
            if (decklistWin) {
                decklistWin.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
            }

            // Small delay so scroll settles before we lock the UI with loading state
            await new Promise(r => setTimeout(r, 120));
            this.decklistPreview();
        } catch (e) {
            this._top8ShowError(`Could not load deck: ${e.message}`);
        }
    },

    _top8ShowError(msg) {
        const errorDiv = document.getElementById('top8Error');
        if (!errorDiv) return;
        errorDiv.textContent = msg;
        errorDiv.style.display = 'block';
        const list = document.getElementById('top8DeckList');
        if (list) list.innerHTML = '';
    },
});
