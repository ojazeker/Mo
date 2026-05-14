import { Mo } from './core.js';

Object.assign(Mo.prototype, {
    setupMomirListeners() {
        const panel = document.querySelector('.momir-window');
        panel.querySelectorAll('.numpad-btn:not(.clear):not(.avatar-info)').forEach(btn => {
            btn.addEventListener('click', () => this.appendCMCDigit(btn.dataset.value));
        });
        document.getElementById('clearBtn').addEventListener('click', () => this.clear());
        document.getElementById('momirAvatarBtn').addEventListener('click', () => this._showAvatarSection('inputSection', 'cardSection', 'momirAvatarSection'));
        document.getElementById('momirAvatarBackBtn').addEventListener('click', () => this._hideAvatarSection('inputSection', 'momirAvatarSection'));
        document.getElementById('momirAvatarPrintBtn').addEventListener('click', () => this._printAvatar('momir_avatar', 'momirAvatarPrintBtn'));
        document.getElementById('printBtn').addEventListener('click', () => this.getRandomCard());
        document.getElementById('newCardBtn').addEventListener('click', () => this.getRandomCard());
        document.getElementById('homeBtn').addEventListener('click', () => this.goHome());
    },

    appendCMCDigit(digit) {
        this.currentCMC = (this.currentCMC === '' ? '' : this.currentCMC) + digit;
        this.hasSelectedCMC = true;
        this.updateDisplay();
        document.getElementById('printBtn').disabled = false;
    },

    clear() {
        this.currentCMC = '';
        this.hasSelectedCMC = false;
        this.updateDisplay();
        document.getElementById('printBtn').disabled = true;
    },

    updateDisplay() {
        document.getElementById('cmcValue').textContent = this.currentCMC;
    },

    async getRandomCard() {
        if (!this.hasSelectedCMC) return;
        this.showLoading(true);
        document.getElementById('errorMessage').style.display = 'none';
        try {
            const response = await fetch(`/api/card/${this.cardType}/${this.currentCMC}`);
            const data = await response.json();
            if (response.ok && data.success) {
                this.currentCard = data;
                this.displayCard(data);
                this.showCardSection(true);
            } else {
                this.showError(data.error || 'Card not found');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showError(`Error: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    },

    displayCard(card) {
        const cardImage = document.getElementById('cardImage');
        this.updateCardRulesText(card);
        if (card.hasLocalImage && card.imageUrl) {
            cardImage.src = card.imageUrl;
            cardImage.alt = card.name;
            cardImage.style.display = 'block';
            this.showError('');
            return;
        }
        cardImage.removeAttribute('src');
        cardImage.alt = '';
        cardImage.style.display = 'none';
        this.showError('No local dithered image found for this card.');
    },

    updateCardRulesText(card) {
        const rulesEl = document.getElementById('cardRulesText');
        if (!rulesEl) return;
        const rulesText = (card?.text || '').trim();
        if (rulesText) {
            rulesEl.textContent = rulesText;
            return;
        }
        const fallbackParts = [];
        if (card?.type) fallbackParts.push(`Type: ${card.type}`);
        if (card?.power && card?.toughness && card.power !== '?' && card.toughness !== '?') {
            fallbackParts.push(`P/T: ${card.power}/${card.toughness}`);
        }
        rulesEl.textContent = fallbackParts.join(' | ') || 'No rules text available for this card.';
    },

    showCardSection(show) {
        document.getElementById('cardSection').style.display = show ? 'block' : 'none';
        document.getElementById('inputSection').style.display = show ? 'none' : 'block';
    },

    showLoading(show) {
        document.getElementById('loadingState').style.display = show ? 'flex' : 'none';
    },

    showError(message) {
        const errorDiv = document.getElementById('errorMessage');
        if (message) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            this.showCardSection(true);
            return;
        }
        errorDiv.textContent = '';
        errorDiv.style.display = 'none';
    },

    goHome() {
        this.showCardSection(false);
        this.clear();
    },
});
