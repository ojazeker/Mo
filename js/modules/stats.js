import { Mo } from './core.js';

Object.assign(Mo.prototype, {
    async loadStats() {
        const statsEl = document.getElementById('statsInfo');
        if (!statsEl) return;
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            const creatureCount = stats.cards_by_type?.creature || stats.total_creatures || 0;
            const tokenCount = stats.total_tokens || 0;
            const typeEntries = Object.entries(stats.cards_by_type || {})
                .map(([t, n]) => `${t.charAt(0).toUpperCase() + t.slice(1)}: ${n}`)
                .join(' / ');
            statsEl.innerHTML = `<span>${typeEntries || `Creatures: ${creatureCount}`} / Tokens: ${tokenCount}</span>`;
        } catch (error) {
            console.error('Could not load stats:', error);
        }
    },
});
