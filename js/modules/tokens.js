import { Mo } from './core.js';

Object.assign(Mo.prototype, {
    setupTokenListeners() {
        document.getElementById('tokenHomeBtn').addEventListener('click', () => this.goTokenHome());
        document.getElementById('printTokenBtn').addEventListener('click', () => this.printCurrentToken());
        document.querySelectorAll('#tokenSearchSection .keyboard-key[data-letter]').forEach(btn => {
            btn.addEventListener('click', () => this.appendTokenLetter(btn.dataset.letter));
        });
        document.getElementById('keyboardClearBtn').addEventListener('click', () => this.clearTokenSearch());
        document.getElementById('keyboardBackspaceBtn').addEventListener('click', () => this.tokenBackspace());
        document.getElementById('keyboardSpaceBtn').addEventListener('click', () => this.appendTokenLetter(' '));
    },

    appendTokenLetter(letter) {
        this.tokenQuery += letter;
        this.updateTokenSearchDisplay();
        if (this.tokenQuery.length >= 2) {
            this.searchTokens();
        } else {
            this.renderTokenResults([]);
        }
    },

    clearTokenSearch() {
        this.tokenQuery = '';
        this.updateTokenSearchDisplay();
        this.renderTokenResults([]);
    },

    tokenBackspace() {
        if (!this.tokenQuery.length) return;
        this.tokenQuery = this.tokenQuery.slice(0, -1);
        this.updateTokenSearchDisplay();
        if (this.tokenQuery.length >= 2) {
            this.searchTokens();
        } else {
            this.renderTokenResults([]);
        }
    },

    updateTokenSearchDisplay() {
        const el = document.getElementById('tokenSearchValue');
        el.textContent = this.tokenQuery;
        el.classList.toggle('is-placeholder', !this.tokenQuery);
    },

    async searchTokens() {
        try {
            const response = await fetch(`/api/tokens/search?q=${encodeURIComponent(this.tokenQuery)}`);
            const data = await response.json();
            if (response.ok) {
                this.renderTokenResults(data.results || []);
            } else {
                this.renderTokenResults([]);
            }
        } catch (error) {
            console.error('Token search error:', error);
            this.renderTokenResults([]);
        }
    },

    async selectToken(tokenId) {
        this.showLoading(true);
        this.showTokenError('');
        try {
            const response = await fetch(`/api/token/${tokenId}`);
            const data = await response.json();
            if (response.ok && data.success) {
                this.currentCard = data;
                this.displayToken(data);
                this.showTokenSection(true);
                const tokenImg = document.getElementById('tokenImage');
                const scrollToTokenWindow = () => {
                    const tokenWindow = document.querySelector('.token-window');
                    if (tokenWindow) {
                        const top = tokenWindow.getBoundingClientRect().top + window.scrollY - 8;
                        window.scrollTo({ top, behavior: 'smooth' });
                    }
                };
                if (tokenImg && tokenImg.src) {
                    tokenImg.addEventListener('load', scrollToTokenWindow, { once: true });
                    tokenImg.addEventListener('error', scrollToTokenWindow, { once: true });
                } else {
                    scrollToTokenWindow();
                }
            } else {
                this.showTokenError(data.error || 'Token not found');
            }
        } catch (error) {
            console.error('Token load error:', error);
            this.showTokenError(`Error: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    },

    renderTokenResults(results) {
        const container = document.getElementById('tokenResults');
        if (this.tokenQuery.length < 2) {
            container.innerHTML = '<div class="token-result-empty">Type 2 letters to search</div>';
            return;
        }
        if (!results.length) {
            container.innerHTML = '<div class="token-result-empty">No tokens found</div>';
            return;
        }
        container.innerHTML = '';
        
        results.forEach((token) => {
            const button = document.createElement('button');
            button.className = 'token-result-btn';
            button.type = 'button';
            const pips = this.buildColorPips(Array.isArray(token.colors) ? token.colors : []);
            const pt = (token.power !== '' && token.toughness !== '')
                ? `<span class="token-pt">${token.power}/${token.toughness}</span>`
                : '';
            const keywords = (token.keywords && token.keywords.length)
                ? `<span class="token-keywords">${token.keywords.join(', ')}</span>`
                : '';
            button.innerHTML = `<div class="token-result-top"><span class="token-name">${token.name}${pips}</span>${pt}</div><div class="token-result-bottom"><span class="token-type-line">${token.type}</span>${keywords}</div>`;
            button.addEventListener('click', () => this.selectToken(token.id));
            container.appendChild(button);
        });
    },

    displayToken(card) {
        const tokenImage = document.getElementById('tokenImage');
        if (card.hasLocalImage && card.imageUrl) {
            tokenImage.src = card.imageUrl;
            tokenImage.alt = card.name;
            tokenImage.style.display = 'block';
            this.showTokenError('');
        } else {
            tokenImage.removeAttribute('src');
            tokenImage.alt = '';
            tokenImage.style.display = 'none';
            this.showTokenError('No local dithered image found for this token.');
        }
        const rulesEl = document.getElementById('tokenRulesText');
        if (rulesEl) {
            const keywords = Array.isArray(card.keywords) ? card.keywords : [];
            let oracleText = (card.oracle_text || '').trim();
            if (keywords.length) {
                const lines = oracleText.split('\n').filter(line => {
                    const trimmed = line.trim();
                    return !keywords.some(kw => trimmed.toLowerCase().startsWith(kw.toLowerCase()));
                });
                oracleText = lines.join('\n').trim();
            }
            const parts = [];
            if (keywords.length) parts.push(keywords.join(', '));
            if (oracleText) parts.push(oracleText);
            rulesEl.textContent = parts.join('\n') || '';
            rulesEl.style.display = parts.length ? 'block' : 'none';
        }
    },

    showTokenSection(show) {
        document.getElementById('tokenPreviewSection').style.display = show ? 'block' : 'none';
        document.getElementById('tokenSearchSection').style.display = show ? 'none' : 'block';
    },

    showTokenError(message) {
        const errorDiv = document.getElementById('tokenErrorMessage');
        if (message) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            this.showTokenSection(true);
            return;
        }
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
    },

    async printCurrentToken() {
        if (!this.currentCard || !this.currentCard.id) return;
        const btn = document.getElementById('printTokenBtn');
        btn.disabled = true;
        btn.textContent = 'Printing...';
        try {
            const response = await fetch(`/api/print/token/${this.currentCard.id}`, { method: 'POST' });
            const data = await response.json();
            if (!data.success) this.showTokenError(data.error || 'Print failed');
        } catch (error) {
            console.error('Print error:', error);
            this.showTokenError(`Print error: ${error.message}`);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Print';
        }
    },

    goTokenHome() {
        this.showTokenSection(false);
        this.showTokenError('');
    },
});
