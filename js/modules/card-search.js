import { Mo } from './core.js';

Object.assign(Mo.prototype, {
    setupCardSearchListeners() {
        document.querySelectorAll('#cardSearchKeyboard .keyboard-key[data-card-letter]').forEach(btn => {
            btn.addEventListener('click', () => this.appendCardSearchLetter(btn.dataset.cardLetter));
        });
        document.getElementById('cardSearchClearBtn').addEventListener('click', () => this.clearCardSearch());
        document.getElementById('cardSearchBackspaceBtn').addEventListener('click', () => this.cardSearchBackspace());
        document.getElementById('cardSearchSpaceBtn').addEventListener('click', () => this.appendCardSearchLetter(' '));
        document.getElementById('cardSearchHomeBtn').addEventListener('click', () => this.goCardSearchHome());
        document.getElementById('printCardSearchBtn').addEventListener('click', () => this.printCurrentCardSearch());
    },

    appendCardSearchLetter(letter) {
        this.cardSearchQuery += letter;
        this.updateCardSearchDisplay();
        if (this.cardSearchQuery.length >= 3) {
            this.renderCardResultsSearching();
            this._debounceCardSearch();
        } else {
            this.renderCardResults([]);
        }
    },

    clearCardSearch() {
        this.cardSearchQuery = '';
        this.updateCardSearchDisplay();
        clearTimeout(this._cardSearchTimer);
        this.renderCardResults([]);
    },

    cardSearchBackspace() {
        if (!this.cardSearchQuery.length) return;
        this.cardSearchQuery = this.cardSearchQuery.slice(0, -1);
        this.updateCardSearchDisplay();
        if (this.cardSearchQuery.length >= 3) {
            clearTimeout(this._cardSearchTimer);
            this._debounceCardSearch();
        } else {
            clearTimeout(this._cardSearchTimer);
            this.renderCardResults([]);
        }
    },

    _debounceCardSearch() {
        clearTimeout(this._cardSearchTimer);
        this._cardSearchTimer = setTimeout(() => this.searchCards(), 300);
    },

    updateCardSearchDisplay() {
        const el = document.getElementById('cardSearchValue');
        el.textContent = this.cardSearchQuery;
        el.classList.toggle('is-placeholder', !this.cardSearchQuery);
    },

    async searchCards() {
        const queryAtStart = this.cardSearchQuery;
        try {
            const response = await fetch(`/api/cards/search?q=${encodeURIComponent(queryAtStart)}`);
            const data = await response.json();
            if (this.cardSearchQuery !== queryAtStart) return;
            if (response.ok) {
                this.renderCardResults(data.results || []);
            } else {
                this.renderCardResults([]);
            }
        } catch (error) {
            if (this.cardSearchQuery !== queryAtStart) return;
            console.error('Card search error:', error);
            this.renderCardResults([]);
        }
    },

    async selectCardSearch(cmc, filename, text, cardType) {
        this.showCardSearchError('');
        this.currentCardSearchCard = { cmc, filename, cardType: cardType || 'creature' };
        const img = document.getElementById('cardSearchImage');
        img.src = `/api/image/${cardType || 'creature'}/${cmc}/${encodeURIComponent(filename)}`;
        img.alt = filename;
        img.style.display = 'block';
        document.getElementById('cardSearchRulesText').textContent = text.trim();
        this.showCardSearchSection(true);
        const scrollToCardWindow = () => {
            const cardSearchWindow = document.querySelector('.card-search-window');
            if (cardSearchWindow) {
                const top = cardSearchWindow.getBoundingClientRect().top + window.scrollY - 8;
                window.scrollTo({ top, behavior: 'smooth' });
            }
        };
        img.addEventListener('load', scrollToCardWindow, { once: true });
        img.addEventListener('error', scrollToCardWindow, { once: true });
    },

    renderCardResultsSearching() {
        const container = document.getElementById('cardSearchResults');
        container.innerHTML = '<div class="token-result-empty">Searching...</div>';
    },

    renderCardResults(results) {
        const container = document.getElementById('cardSearchResults');
        if (this.cardSearchQuery.length < 3) {
            container.innerHTML = '<div class="token-result-empty">Type 3 letters to search</div>';
            return;
        }
        if (!results.length) {
            container.innerHTML = '<div class="token-result-empty">No cards found</div>';
            return;
        }
        container.innerHTML = '';
        results.forEach((card) => {
            const button = document.createElement('button');
            button.className = 'token-result-btn';
            button.type = 'button';
            const isCreature = card.card_type === 'creature';
            const pt = (isCreature && card.power !== '' && card.toughness !== '' && card.power !== '?' && card.toughness !== '?')
                ? `<span class="token-pt">${card.power}/${card.toughness}</span>`
                : '';
            const pips = this.buildColorPips(this.colorsFromManaCost(card.manaCost || ''));
            const cmc = card.cmc !== undefined ? `<span class="token-pt">CMC ${card.cmc}</span>` : '';
            button.innerHTML = `<div class="token-result-top"><span class="token-name">${card.name}${pips}</span>${pt}</div><div class="token-result-top"><span class="token-type-line">${card.type}</span>${cmc}</div>`;
            button.addEventListener('click', () => this.selectCardSearch(card.cmc, card.filename, card.text || '', card.card_type || 'creature'));
            container.appendChild(button);
        });
    },

    showCardSearchSection(show) {
        document.getElementById('cardSearchPreviewSection').style.display = show ? 'block' : 'none';
        document.getElementById('cardSearchSection').style.display = show ? 'none' : 'block';
    },

    showCardSearchError(message) {
        const errorDiv = document.getElementById('cardSearchErrorMessage');
        if (message) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            return;
        }
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
    },

    async printCurrentCardSearch() {
        if (!this.currentCardSearchCard) return;
        const { cmc, filename, cardType } = this.currentCardSearchCard;
        const btn = document.getElementById('printCardSearchBtn');
        btn.disabled = true;
        btn.textContent = 'Printing...';
        try {
            const response = await fetch(`/api/print/card/${cardType || 'creature'}/${cmc}/${encodeURIComponent(filename)}`, { method: 'POST' });
            const data = await response.json();
            if (!data.success) this.showCardSearchError(data.error || 'Print failed');
        } catch (error) {
            console.error('Print error:', error);
            this.showCardSearchError(`Print error: ${error.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Print';
        }
    },

    goCardSearchHome() {
        this.showCardSearchSection(false);
        this.showCardSearchError('');
    },
});
