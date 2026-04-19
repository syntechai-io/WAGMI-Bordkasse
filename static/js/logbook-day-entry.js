(function () {
    const tpl = document.getElementById('dayRowTemplate');
    const container = document.getElementById('rowsContainer');
    const addBtn = document.getElementById('addRowBtn');
    const counter = document.getElementById('rowCounter');
    const form = document.getElementById('dayLogbookForm');
    const quickBtn = document.getElementById('quickFillFirstRow');
    const quickStatus = document.getElementById('quickFillStatus');

    if (!tpl || !container) return;

    const i18n = {
        rowRequired: form ? form.dataset.i18nRowRequired || 'At least one row is required.' : 'At least one row is required.',
        timeMissing: form ? form.dataset.i18nTimeMissing || 'Time missing in row {n}.' : 'Time missing in row {n}.',
        timeMonotonic: form ? form.dataset.i18nTimeMonotonic || 'Row {n}: time {time} is before previous ({prev}).' : 'Row {n}: time {time} is before previous ({prev}).',
        minRow: form ? form.dataset.i18nMinRow || 'At least one row required.' : 'At least one row required.',
        photosSelected: form ? form.dataset.i18nPhotosSelected || '{n} selected' : '{n} selected'
    };
    function fmt(tpl, vars) {
        return tpl.replace(/\{(\w+)\}/g, (_, k) => vars[k] != null ? vars[k] : '');
    }

    function renumber() {
        const rows = container.querySelectorAll('.day-row');
        rows.forEach((r, i) => {
            const idx = r.querySelector('.row-index');
            if (idx) idx.textContent = '#' + (i + 1);
        });
        if (counter) counter.textContent = rows.length;
    }

    function carryForward(newRow) {
        const rows = container.querySelectorAll('.day-row');
        if (rows.length === 0) return;
        const prev = rows[rows.length - 1];
        // Carry: latitude, longitude, wind_direction, wind_strength, sea_state, visibility, temperature, sail_plan, eng_hours_total
        const carryFields = [
            'row_latitude', 'row_longitude', 'row_wind_direction',
            'row_wind_strength', 'row_sea_state', 'row_visibility',
            'row_temperature', 'row_sail_plan', 'row_engine_on',
            'row_eng_hours_total'
        ];
        carryFields.forEach(name => {
            const prevField = prev.querySelector('[name="' + name + '"]');
            const newField = newRow.querySelector('[name="' + name + '"]');
            if (prevField && newField && prevField.value && !newField.value) {
                newField.value = prevField.value;
            }
        });
        // Auto-increment time by 1 hour
        const prevTime = prev.querySelector('[name="row_time"]');
        const newTime = newRow.querySelector('[name="row_time"]');
        if (prevTime && prevTime.value && newTime && !newTime.value) {
            const [hh, mm] = prevTime.value.split(':').map(Number);
            const next = (hh + 1) % 24;
            newTime.value = String(next).padStart(2, '0') + ':' + String(mm).padStart(2, '0');
        }
    }

    function addRow(opts) {
        opts = opts || {};
        const clone = tpl.content.cloneNode(true);
        const row = clone.querySelector('.day-row');
        if (!opts.skipCarry) carryForward(row);
        // Default first row time
        if (container.children.length === 0) {
            const t = row.querySelector('[name="row_time"]');
            if (t && !t.value) {
                const now = new Date();
                t.value = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
            }
        }
        // Wire remove button
        const removeBtn = row.querySelector('.remove-row-btn');
        if (removeBtn) {
            removeBtn.addEventListener('click', function () {
                if (container.children.length <= 1) {
                    alert(i18n.minRow);
                    return;
                }
                row.remove();
                renumber();
            });
        }
        container.appendChild(row);
        renumber();
        return row;
    }

    addBtn.addEventListener('click', function () { addRow(); });

    // Quick Fill seeds first row from GPS + weather
    if (quickBtn) {
        quickBtn.addEventListener('click', async function () {
            const firstRow = container.querySelector('.day-row');
            if (!firstRow) return;
            quickStatus.textContent = '⏳ ...';
            try {
                if (!navigator.geolocation) throw new Error('GPS not available');
                const pos = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject, {
                        enableHighAccuracy: true, timeout: 10000, maximumAge: 0
                    });
                });
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                const latField = firstRow.querySelector('[name="row_latitude"]');
                const lonField = firstRow.querySelector('[name="row_longitude"]');
                if (latField) latField.value = lat.toFixed(6);
                if (lonField) lonField.value = lon.toFixed(6);
                // Set time to now
                const t = firstRow.querySelector('[name="row_time"]');
                if (t) {
                    const now = new Date();
                    t.value = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
                }
                // Try fetch weather
                try {
                    const wr = await fetch(`/api/weather?lat=${lat}&lon=${lon}`);
                    if (wr.ok) {
                        const w = await wr.json();
                        const td = firstRow.querySelector('[name="row_temperature"]');
                        const wd = firstRow.querySelector('[name="row_wind_direction"]');
                        const ws = firstRow.querySelector('[name="row_wind_strength"]');
                        if (td && w.temperature != null) td.value = w.temperature;
                        if (wd && w.wind_direction) wd.value = w.wind_direction;
                        if (ws && (w.wind_strength_bft != null || w.wind_bft != null)) {
                            ws.value = String(w.wind_strength_bft != null ? w.wind_strength_bft : w.wind_bft);
                        }
                    }
                } catch (we) { /* weather optional */ }
                quickStatus.textContent = '✅';
                quickStatus.style.color = 'var(--success)';
            } catch (e) {
                quickStatus.textContent = '❌ ' + (e.message || e);
                quickStatus.style.color = 'var(--coral)';
            }
        });
    }

    // Validate: times monotonic and ≥1 row
    if (form) {
        form.addEventListener('submit', function (ev) {
            const rows = container.querySelectorAll('.day-row');
            if (rows.length === 0) {
                ev.preventDefault();
                alert(i18n.rowRequired);
                return;
            }
            let lastT = null;
            for (let i = 0; i < rows.length; i++) {
                const tv = rows[i].querySelector('[name="row_time"]').value;
                if (!tv) {
                    ev.preventDefault();
                    alert(fmt(i18n.timeMissing, {n: i + 1}));
                    return;
                }
                if (lastT && tv < lastT) {
                    ev.preventDefault();
                    alert(fmt(i18n.timeMonotonic, {n: i + 1, time: tv, prev: lastT}));
                    return;
                }
                lastT = tv;
            }
        });
    }

    // Initial first row
    addRow({ skipCarry: true });

    // Day-photos count
    const dayPhotos = document.getElementById('dayPhotosInput');
    const dayPhotosCount = document.getElementById('dayPhotosCount');
    if (dayPhotos && dayPhotosCount) {
        dayPhotos.addEventListener('change', function() {
            dayPhotosCount.textContent = dayPhotos.files.length
                ? fmt(i18n.photosSelected, {n: dayPhotos.files.length})
                : '';
        });
    }
})();
