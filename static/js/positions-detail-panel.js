/**
 * Panneau de détail en lecture seule pour la page Positions (Spot/Futures fusionnée).
 * Aucune donnée n'est modifiable ici : ce panneau remplace les anciennes modales d'édition.
 */
(function () {
    const overlay = document.getElementById('detailPanelOverlay');
    const panel = document.getElementById('detailPanel');
    const title = document.getElementById('detailPanelTitle');
    const body = document.getElementById('detailPanelBody');
    const closeBtn = document.getElementById('detailPanelClose');

    if (!overlay || !body) return;

    const FIELD_LABELS = [
        ['entryDate', "Date d'entrée"],
        ['amount', 'Quantité'],
        ['entryPrice', "Prix d'entrée"],
        ['exitPrice', 'Prix de sortie'],
        ['exitPrice2', 'Prix de sortie (2e)'],
        ['takeProfit', 'Take profit'],
        ['stopLoss', 'Stop loss'],
        ['timeframe', 'Time frame'],
        ['tradeMode', 'Mode'],
        ['exchange', 'Exchange'],
        ['direction', 'Direction'],
        ['strategy', 'Stratégie'],
        ['feeling', 'Ressenti'],
        ['riskRewardRatio', 'Ratio risque/rendement'],
        ['why', 'Raison de la prise de position'],
        ['notes', 'Notes'],
    ];

    function openPanelFor(row) {
        const data = row.dataset;
        title.textContent = `${data.symbol || ''}`;
        body.innerHTML = '';
        FIELD_LABELS.forEach(([key, label]) => {
            const value = data[key];
            if (!value) return;
            const dt = document.createElement('dt');
            dt.textContent = label;
            const dd = document.createElement('dd');
            dd.textContent = value;
            body.appendChild(dt);
            body.appendChild(dd);
        });
        overlay.classList.add('active');
    }

    function closePanel() {
        overlay.classList.remove('active');
    }

    document.querySelectorAll('.position-row').forEach((row) => {
        row.addEventListener('click', (event) => {
            // Ignorer les clics sur les actions (suppression) pour ne pas ouvrir le panneau par erreur.
            if (event.target.closest('.investments-table-actions')) return;
            openPanelFor(row);
        });
        const detailsBtn = row.querySelector('.icon-details');
        if (detailsBtn) {
            detailsBtn.addEventListener('click', (event) => {
                event.stopPropagation();
                openPanelFor(row);
            });
        }
    });

    if (closeBtn) closeBtn.addEventListener('click', closePanel);
    overlay.addEventListener('click', (event) => {
        if (event.target === overlay) closePanel();
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closePanel();
    });
})();
