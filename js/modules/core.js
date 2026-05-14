export class Mo {
    constructor() {
        this.currentCMC = '';
        this.hasSelectedCMC = false;
        this.currentCard = null;
        this.cardType = 'creature';
        this.tokenQuery = '';
        this.cardSearchQuery = '';
        this.currentCardSearchCard = null;
        this.init();
    }

    init() {
        this.initWindowFocusTracking();
        this.setupEventListeners();
        this.loadStats();
        this.updateTokenSearchDisplay();
        this.updateCardSearchDisplay();
        this.renderTokenResults([]);
        this.renderCardResults([]);
    }

    initWindowFocusTracking() {
        this.windows = Array.from(document.querySelectorAll('.window'));
        if (!this.windows.length) return;

        this.setActiveWindow(this.windows[0]);

        this.windows.forEach((windowEl) => {
            windowEl.addEventListener('click', () => this.setActiveWindow(windowEl));
            windowEl.addEventListener('focusin', () => this.setActiveWindow(windowEl));
        });

        document.querySelectorAll('.window-row').forEach((windowRow) => {
            windowRow.addEventListener('scrollend', () => {
                const rowWindows = Array.from(windowRow.querySelectorAll('.window'));
                if (!rowWindows.length) return;
                const snapped = rowWindows.reduce((closest, windowEl) => {
                    const dist = Math.abs(windowEl.offsetLeft - windowRow.scrollLeft);
                    return dist < Math.abs(closest.offsetLeft - windowRow.scrollLeft) ? windowEl : closest;
                });
                this.setActiveWindow(snapped);
            });
        });
    }

    setActiveWindow(activeWindow) {
        if (!this.windows || !this.windows.length) return;
        this.windows.forEach((windowEl) => {
            windowEl.classList.toggle('is-active-window', windowEl === activeWindow);
        });
    }

    setupEventListeners() {
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
        this.setupMomirListeners();
        this.setupTokenListeners();
        this.setupCardSearchListeners();
        this.setupStonehewerListeners();
        this.setupJhoiraListeners();
        this.setupDecklistListeners();
        this.setupTop8Listeners();
    }

    handleKeyboard(e) {
        if (e.key >= '0' && e.key <= '9') {
            this.appendCMCDigit(e.key);
        }
        if (e.key === 'Backspace' || e.key === 'Delete') this.clear();
        if (e.key === 'Enter') this.getRandomCard();
    }
}
