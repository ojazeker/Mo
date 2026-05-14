import { Mo } from './core.js';

Object.assign(Mo.prototype, {
    setupJhoiraListeners() {
        this.jhoiraType = 'instant';
        this.currentJhoiraCard = null;
        document.getElementById('jhoiraPreviewBtn').addEventListener('click', () => this.jhPreview());
        document.getElementById('jhoiraNextBtn').addEventListener('click', () => this.jhPreview());
        document.getElementById('jhoiraHomeBtn').addEventListener('click', () => this._showWindowSection('jhoiraInputSection', 'jhoiraCardSection', false));
        document.querySelectorAll('.jhoira-type-toggle .type-toggle-btn[data-type]').forEach(btn => {
            btn.addEventListener('click', () => this.jhSetType(btn.dataset.type));
        });
        document.getElementById('jhoiraAvatarBtn').addEventListener('click', () => this._showAvatarSection('jhoiraInputSection', 'jhoiraCardSection', 'jhoiraAvatarSection'));
        document.getElementById('jhoiraAvatarBackBtn').addEventListener('click', () => this._hideAvatarSection('jhoiraInputSection', 'jhoiraAvatarSection'));
        document.getElementById('jhoiraAvatarPrintBtn').addEventListener('click', () => this._printAvatar('jhoira_avatar', 'jhoiraAvatarPrintBtn'));
    },

    jhSetType(type) {
        this.jhoiraType = type;
        document.querySelectorAll('.jhoira-type-toggle .type-toggle-btn[data-type]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === type);
        });
    },

    async jhPreview() {
        document.getElementById('jhoiraLoadingState').style.display = 'flex';
        document.getElementById('jhoiraInputSection').style.display = 'none';
        document.getElementById('jhoiraCardSection').style.display = 'none';
        try {
            const seen = new Set();
            const successes = [];
            let attempts = 0;
            while (successes.length < 3 && attempts < 15) {
                const card = await fetch(`/api/card/random/${this.jhoiraType}?preview_only=true`).then(r => r.json());
                if (card.success && !seen.has(card.imageUrl)) {
                    seen.add(card.imageUrl);
                    successes.push(card);
                }
                attempts++;
            }
            document.getElementById('jhoiraLoadingState').style.display = 'none';
            if (!successes.length) {
                document.getElementById('jhoiraInputSection').style.display = 'block';
                const err = document.getElementById('jhoiraErrorMessage');
                err.textContent = 'No cards found.';
                err.style.display = 'block';
                return;
            }
            document.getElementById('jhoiraErrorMessage').style.display = 'none';
            this.currentJhoiraCards = successes;
            const container = document.getElementById('jhoiraCards');
            container.innerHTML = '';
            successes.forEach((card, index) => {
                const wrap = document.createElement('div');
                wrap.className = 'jhoira-card-entry' + (index === 0 ? ' active' : '');
                if (card.hasLocalImage && card.imageUrl) {
                    const img = document.createElement('img');
                    img.className = 'card-image';
                    img.src = card.imageUrl;
                    img.alt = card.name || '';
                    wrap.appendChild(img);
                }
                const rules = document.createElement('div');
                rules.className = 'card-rules-text';
                rules.textContent = (card.text || '').trim() || card.type || '';
                wrap.appendChild(rules);
                container.appendChild(wrap);
            });
            if (this._jhoiraClickHandler) {
                container.removeEventListener('click', this._jhoiraClickHandler);
            }
            this._jhoiraClickHandler = () => {
                const entries = [...container.querySelectorAll('.jhoira-card-entry')];
                const activeIndex = entries.findIndex(el => el.classList.contains('active'));
                const nextIndex = (activeIndex + 1) % entries.length;
                entries.forEach((el, i) => el.classList.toggle('active', i === nextIndex));
                this._updateJhoiraOrder(container);
            };
            container.addEventListener('click', this._jhoiraClickHandler);
            this._updateJhoiraOrder(container);
            this._showWindowSection('jhoiraInputSection', 'jhoiraCardSection', true);
        } catch (e) {
            document.getElementById('jhoiraLoadingState').style.display = 'none';
            document.getElementById('jhoiraInputSection').style.display = 'block';
            console.error('Jhoira preview failed:', e);
        }
    },

    _updateJhoiraOrder(container) {
        const orderClasses = ['first', 'second', 'third'];
        let orderIndex = 0;
        container.querySelectorAll('.jhoira-card-entry').forEach(entry => {
            entry.classList.remove('first', 'second', 'third');
            if (!entry.classList.contains('active')) {
                entry.classList.add(orderClasses[orderIndex++] || 'third');
            }
        });
    },
});
