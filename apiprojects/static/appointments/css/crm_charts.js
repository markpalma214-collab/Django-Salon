/* Shared Chart.js setup for the CRM pages (dashboard and revenue analysis).
   Load after Chart.js and after crm_theme.css. Place at static/crm_dashboard/crm_charts.js */
window.CRM = (function () {
    var FALLBACK = {
        '--crm-red-600': '#a30f24', '--crm-red-400': '#d9475c', '--crm-red-200': '#f0a8b2',
        '--crm-copper': '#b9784a', '--crm-sand': '#e6cdb0', '--crm-ink-900': '#201417',
        '--crm-ink-500': '#6a5a5e', '--crm-line': '#ebdfe1'
    };
    var styles = getComputedStyle(document.documentElement);

    function token(name) {
        return styles.getPropertyValue(name).trim() || FALLBACK[name];
    }

    function alpha(hex, a) {
        var n = parseInt(hex.slice(1), 16);
        return 'rgba(' + (n >> 16) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
    }

    function peso(v) {
        return '₱' + Number(v).toLocaleString('en-PH', { maximumFractionDigits: 0 });
    }

    function pesoFull(v) {
        return '₱' + Number(v).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    // Ordered so neighbouring slices stay easy to tell apart
    var palette = ['--crm-red-600', '--crm-copper', '--crm-red-200', '--crm-ink-500', '--crm-red-400', '--crm-sand'].map(token);

    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.font.size = 12;
    Chart.defaults.color = token('--crm-ink-500');
    Chart.defaults.borderColor = token('--crm-line');
    Chart.defaults.plugins.tooltip.backgroundColor = token('--crm-ink-900');
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.plugins.tooltip.boxPadding = 4;

    return { token: token, alpha: alpha, peso: peso, pesoFull: pesoFull, palette: palette };
})();