/* Shared chart kit for the Hub's real-estate pages.
 *
 * ma-housing-dashboard.html, nh-housing-dashboard.html and
 * haverhill-market-report.html all draw from this so the three read as one
 * instrument. Change a colour or a mark spec HERE, never on a page.
 *
 * ---------------------------------------------------------------------------
 * THE PALETTE IS NOT A TASTE DECISION. It was produced by the dataviz
 * validator, and the order below is part of the result.
 *
 * What was here before FAILED two checks, live, on all three pages:
 *   - #2A6B44 had chroma 0.092, under the floor: it rendered as grey.
 *   - #2A6B44 vs #A81733 was deltaE 3.8 for deuteranopes. The red and green
 *     series were THE SAME COLOUR to red-green colourblind readers.
 *
 * The brand cranberry #680A1D cannot be a series colour: L 0.335 sits outside
 * the 0.43-0.77 band. It stays in headers and text, where it is correct.
 *
 * Validated, light surface, all five checks PASS:
 *   node scripts/validate_palette.js "#14558F,#B01A36,#C98A1E,#2E8B57" --mode light
 *
 * ORDER MATTERS. The validator scores ADJACENT pairs, and red next to green is
 * the pair that fails. Gold sits between them on purpose. Putting cranberry
 * beside berkshire green re-breaks CVD separation, so add new series at the
 * END of CATEGORICAL and never reorder it.
 *
 * Two standing obligations the validator attached to this palette:
 *   1. Harbor Gold contrasts 2.87:1 against the page surface, under 3:1. Any
 *      chart using it needs visible labels or a table view. Never gold alone
 *      carrying a value a reader has to recover from the picture.
 *   2. Dark mode FAILS this palette. These pages are light on purpose and must
 *      stay that way; do not add a dark toggle without re-running the
 *      validator with --mode dark and re-stepping every colour.
 *
 * Re-run the validator after ANY change here. Do not eyeball it.
 * --------------------------------------------------------------------------- */
(function (global) {
    'use strict';

    // Fixed categorical order. Assign by position, never cycle, never reorder.
    var CATEGORICAL = ['#14558F', '#B01A36', '#C98A1E', '#2E8B57'];

    var HUB = {
        bayBlue:        '#14558F',   // slot 1
        cranberry:      '#B01A36',   // slot 2  (chart weight; brand #680A1D is text only)
        harborGold:     '#C98A1E',   // slot 3  (see obligation 1 above)
        berkshireGreen: '#2E8B57',   // slot 4
        ink:            '#0f2942',
        muted:          '#5A6467',
        grid:           '#CDD3D1',
        surface:        '#fcfcfb'
    };

    // Entities keep their colour wherever they appear, on every page, so a
    // reader who learns "blue is Massachusetts" on one page is not retaught on
    // the next. Colour follows the entity, never its rank in a sorted list.
    var ENTITY = {
        ma:          HUB.bayBlue,
        boston:      HUB.cranberry,
        essex:       HUB.berkshireGreen,
        nbpt:        HUB.harborGold,
        haverhill:   HUB.cranberry,
        nh:          HUB.bayBlue,
        portsmouth:  HUB.cranberry,
        salem:       HUB.harborGold,
        derry:       HUB.berkshireGreen,
        windham:     HUB.muted
    };

    var baseOpts = {
        chart: {
            fontFamily: "'DM Sans', sans-serif",
            toolbar: { show: false },
            zoom: { enabled: false },
            animations: {
                enabled: true, easing: 'easeOutCubic', speed: 900,
                animateGradually: { enabled: true, delay: 80 },
                dynamicAnimation: { enabled: true, speed: 400 }
            },
            dropShadow: { enabled: true, top: 4, left: 0, blur: 8, color: HUB.bayBlue, opacity: 0.08 }
        },
        // Recessive grid: the data is the figure, the grid is the ground.
        grid: {
            borderColor: HUB.grid, strokeDashArray: 3,
            xaxis: { lines: { show: false } },
            padding: { left: 8, right: 8 }
        },
        legend: {
            position: 'top', horizontalAlign: 'right',
            fontSize: '12px', fontWeight: 600,
            markers: { width: 10, height: 10, radius: 4 },
            itemMargin: { horizontal: 10, vertical: 4 }
        },
        tooltip: {
            theme: 'light', shared: true, intersect: false,
            style: { fontSize: '12px' }, x: { show: true }
        },
        dataLabels: { enabled: false },
        stroke: { width: 2, curve: 'smooth' },          // thin marks
        markers: { size: 4, hover: { size: 8 } }        // >= 8px hit target on hover
    };

    function fmtMoney(v)     { return v == null ? '—' : '$' + Math.round(v / 1000) + 'K'; }
    function fmtMoneyFull(v) { return v == null ? '—' : '$' + Math.round(v).toLocaleString(); }
    function fmtSqft(v)      { return v == null ? '—' : '$' + Math.round(v); }
    function fmtDom(v)       { return v == null ? '—' : Math.round(v) + 'd'; }
    function fmtPct(v)       { return v == null ? '—' : v.toFixed(1) + '%'; }
    function fmtUnits(v)     { return v == null ? '—' : Math.round(v).toLocaleString(); }
    function fmtK(v)         { return v == null ? '—' : (v >= 1000 ? Math.round(v / 1000) + 'K' : Math.round(v)); }

    /* Index a series to its first non-null point = 100.
     *
     * This is how series of different magnitude belong on one axis. The MA
     * volume chart used to multiply Essex by 10 and Newburyport by 400 to drag
     * them next to a statewide count -- a dual-axis chart in disguise, which is
     * the single most common charting error, and it made the reader do arithmetic
     * to recover a real number. Index instead and the comparison is honest:
     * every line starts at 100 and the shape is the point.
     */
    function indexTo100(arr) {
        var base = null, i;
        for (i = 0; i < arr.length; i++) {
            if (arr[i] != null) { base = arr[i]; break; }
        }
        if (!base) return arr.map(function () { return null; });
        return arr.map(function (v) { return v == null ? null : +(v / base * 100).toFixed(1); });
    }

    /* Tooltip for an indexed chart.
     *
     * An index is only honest if the reader can get back to the real number,
     * so every indexed series shows "112  ($934,000)" rather than a bare 112.
     * rawSeries and fmts are positional, matching the series order.
     */
    function indexedTooltip(rawSeries, fmts) {
        return function (v, opts) {
            if (v == null) return '—';
            var n = rawSeries[opts.seriesIndex][opts.dataPointIndex];
            if (n == null) return v.toFixed(0);
            var f = fmts[opts.seriesIndex];
            return v.toFixed(0) + '  (' + (f ? f(n) : n) + ')';
        };
    }

    global.HubCharts = {
        HUB: HUB,
        CATEGORICAL: CATEGORICAL,
        ENTITY: ENTITY,
        baseOpts: baseOpts,
        indexTo100: indexTo100,
        indexedTooltip: indexedTooltip,
        fmt: {
            money: fmtMoney, moneyFull: fmtMoneyFull, sqft: fmtSqft,
            dom: fmtDom, pct: fmtPct, units: fmtUnits, k: fmtK
        }
    };
})(window);
