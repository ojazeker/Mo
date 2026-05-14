import { Mo } from './core.js';

Object.assign(Mo.prototype, {
    setupStonehewerListeners() {
        this.stonehewerCMC = null;
        this.currentStonehewerCard = null;
        this.stonehewerCMCStr = '';
        document.querySelectorAll('.sh-numpad-btn[data-value]').forEach(btn => {
            btn.addEventListener('click', () => this.shAppendDigit(btn.dataset.value));
        });
        document.getElementById('stonehewerClearBtn').addEventListener('click', () => this.shClear());
        document.getElementById('stonehewerDrawBtn').addEventListener('click', () => this.shDraw());
        document.getElementById('stonehewerHomeBtn').addEventListener('click', () => this._showWindowSection('stonehewerInputSection', 'stonehewerCardSection', false));
        document.getElementById('stonehewerPrintBtn').addEventListener('click', () => this.shPrint());
        document.getElementById('stonehewerAvatarBtn').addEventListener('click', () => this._showAvatarSection('stonehewerInputSection', 'stonehewerCardSection', 'stonehewerAvatarSection'));
        document.getElementById('stonehewerAvatarBackBtn').addEventListener('click', () => this._hideAvatarSection('stonehewerInputSection', 'stonehewerAvatarSection'));
        document.getElementById('stonehewerAvatarPrintBtn').addEventListener('click', () => this._printAvatar('stonehewer_avatar', 'stonehewerAvatarPrintBtn'));
    },

    shAppendDigit(digit) {
        const next = (this.stonehewerCMCStr || '') + digit;
        if (parseInt(next) > 13) return;
        this.stonehewerCMCStr = next;
        const value = parseInt(this.stonehewerCMCStr);
        this.stonehewerCMC = value;
        document.getElementById('stonehewerCmcValue').textContent = `≤ ${this.stonehewerCMCStr}`;
        document.getElementById('stonehewerDrawBtn').disabled = value < 1;
    },

    shClear() {
        this.stonehewerCMC = null;
        this.stonehewerCMCStr = '';
        document.getElementById('stonehewerCmcValue').textContent = '';
        document.getElementById('stonehewerDrawBtn').disabled = true;
    },

    async shDraw() {
        if (this.stonehewerCMC === null || this.stonehewerCMC < 1) return;
        // Build a shuffled list of CMC values from 0 to max-1
        const cmcValues = Array.from({ length: this.stonehewerCMC }, (_, i) => i);
        for (let i = cmcValues.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [cmcValues[i], cmcValues[j]] = [cmcValues[j], cmcValues[i]];
        }
        document.getElementById('stonehewerLoadingState').style.display = 'flex';
        document.getElementById('stonehewerInputSection').style.display = 'none';
        document.getElementById('stonehewerCardSection').style.display = 'none';
        try {
            let card = null;
            for (const cmc of cmcValues) {
                const resp = await fetch(`/api/card/artifact/${cmc}?subtype=Equipment`);
                const data = await resp.json();
                if (resp.ok && data.success) {
                    card = data;
                    break;
                }
            }
            document.getElementById('stonehewerLoadingState').style.display = 'none';
            if (!card) {
                document.getElementById('stonehewerInputSection').style.display = 'block';
                const err = document.getElementById('stonehewerErrorMessage');
                err.textContent = 'No equipment found for any CMC in that range.';
                err.style.display = 'block';
                return;
            }
            document.getElementById('stonehewerErrorMessage').style.display = 'none';
            this.currentStonehewerCard = card;
            this._displayCardInWindow(card, 'stonehewerCardImage', 'stonehewerRulesText');
            this._showWindowSection('stonehewerInputSection', 'stonehewerCardSection', true);
        } catch (e) {
            document.getElementById('stonehewerLoadingState').style.display = 'none';
            document.getElementById('stonehewerInputSection').style.display = 'block';
            console.error('Stonehewer draw failed:', e);
        }
    },

    async shPrint() {
        const card = this.currentStonehewerCard;
        if (!card) return;
        const btn = document.getElementById('stonehewerPrintBtn');
        btn.disabled = true;
        btn.textContent = 'Printing...';
        try {
            const stem = card.imageUrl.split('/').pop();
            await fetch(`/api/print/card/artifact/${card.cmc}/${encodeURIComponent(stem)}`, { method: 'POST' });
        } catch (e) {
            console.error('Stonehewer print failed:', e);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Print';
        }
    },
});
