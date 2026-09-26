/**
 * Panneau de détail en lecture seule, réutilisable pour toute table de données
 * (Positions, Trading — positions ouvertes...). Chaque ligne cliquable porte la
 * classe `.detail-row` et ses données en attributs `data-*` ; ce script se contente
 * d'afficher les champs présents, dans l'ordre de FIELD_LABELS. Aucune donnée
 * n'est modifiable ici — la suppression/clôture reste déléguée aux boutons
 * d'action existants de chaque ligne.
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
        ['price', 'Prix'],
        ['entryPrice', "Prix d'entrée"],
        ['currentPrice', 'Prix actuel'],
        ['exitPrice', 'Prix de sortie'],
        ['exitPrice2', 'Prix de sortie (2e)'],
        ['pnl', 'PnL latent'],
        ['takeProfit', 'Take profit'],
        ['stopLoss', 'Stop loss'],
        ['timeframe', 'Time frame'],
        ['tradeMode', 'Mode'],
        ['exchange', 'Exchange'],
        ['direction', 'Direction'],
        ['action', "Type d'opération"],
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

    function wireRow(row) {
        row.addEventListener('click', (event) => {
            // Ignorer les clics sur les actions (suppression/clôture) pour ne pas ouvrir le panneau par erreur.
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
    }

    document.querySelectorAll('.detail-row').forEach(wireRow);
    // Certaines tables (positions ouvertes de Trading) se re-rendent en JS via
    // fetch/polling : exposer wireRow pour que ce code puisse câbler les nouvelles
    // lignes sans dupliquer la logique du panneau.
    window.wireDetailRow = wireRow;

    if (closeBtn) closeBtn.addEventListener('click', closePanel);
    overlay.addEventListener('click', (event) => {
        if (event.target === overlay) closePanel();
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closePanel();
    });
})();
