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
            const upBtn = r.querySelector('.move-up-btn');
            const downBtn = r.querySelector('.move-down-btn');
            if (upBtn) upBtn.disabled = (i === 0);
            if (downBtn) downBtn.disabled = (i === rows.length - 1);
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

    function moveRow(row, delta) {
        const rows = Array.from(container.querySelectorAll('.day-row'));
        const idx = rows.indexOf(row);
        if (idx < 0) return;
        const target = idx + delta;
        if (target < 0 || target >= rows.length) return;
        if (delta < 0) {
            container.insertBefore(row, rows[target]);
        } else {
            container.insertBefore(row, rows[target].nextSibling);
        }
        renumber();
    }

    function wireReorder(row) {
        const handle = row.querySelector('.drag-handle');
        const upBtn = row.querySelector('.move-up-btn');
        const downBtn = row.querySelector('.move-down-btn');
        if (upBtn) upBtn.addEventListener('click', function () { moveRow(row, -1); });
        if (downBtn) downBtn.addEventListener('click', function () { moveRow(row, 1); });
        if (!handle) return;

        handle.addEventListener('pointerdown', function (ev) {
            ev.preventDefault();
            try { handle.setPointerCapture(ev.pointerId); } catch (e) {}
            row.classList.add('dragging');
            row.style.opacity = '0.6';
            row.style.boxShadow = '0 4px 16px rgba(0,0,0,0.15)';
            handle.style.cursor = 'grabbing';

            function onMove(e) {
                const y = e.clientY;
                const others = Array.from(container.querySelectorAll('.day-row')).filter(r => r !== row);
                let inserted = false;
                for (const other of others) {
                    const rect = other.getBoundingClientRect();
                    const mid = rect.top + rect.height / 2;
                    if (y < mid) {
                        if (other.previousElementSibling !== row) {
                            container.insertBefore(row, other);
                        }
                        inserted = true;
                        break;
                    }
                }
                if (!inserted && others.length) {
                    const last = others[others.length - 1];
                    if (last.nextElementSibling !== row) {
                        container.appendChild(row);
                    }
                }
            }
            function onUp() {
                row.classList.remove('dragging');
                row.style.opacity = '';
                row.style.boxShadow = '';
                handle.style.cursor = 'grab';
                document.removeEventListener('pointermove', onMove);
                document.removeEventListener('pointerup', onUp);
                document.removeEventListener('pointercancel', onUp);
                renumber();
            }
            document.addEventListener('pointermove', onMove);
            document.addEventListener('pointerup', onUp);
            document.addEventListener('pointercancel', onUp);
        });
    }

    function wireRow(row) {
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
        wireReorder(row);
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
        wireRow(row);
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

    // Wire up server-rendered rows (e.g. after a validation error redisplay).
    // Only auto-add an initial row when none were rendered server-side.
    const existingRows = container.querySelectorAll('.day-row');
    if (existingRows.length === 0) {
        addRow({ skipCarry: true });
    } else {
        existingRows.forEach(wireRow);
        renumber();
        // Scroll to first row with an inline error so the user sees it.
        const firstErr = container.querySelector('.day-row.row-has-error');
        if (firstErr && firstErr.scrollIntoView) {
            firstErr.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    // Day-photos: count + thumbnail previews
    const dayPhotos = document.getElementById('dayPhotosInput');
    const dayPhotosCount = document.getElementById('dayPhotosCount');
    const dayPhotosPreview = document.getElementById('dayPhotosPreview');
    if (dayPhotos) {
        dayPhotos.addEventListener('change', function() {
            const files = Array.from(dayPhotos.files || []);
            if (dayPhotosCount) {
                dayPhotosCount.textContent = files.length
                    ? '✅ ' + fmt(i18n.photosSelected, {n: files.length})
                    : '';
            }
            if (dayPhotosPreview) {
                dayPhotosPreview.innerHTML = '';
                files.forEach(function(f) {
                    if (!f.type || !f.type.startsWith('image/')) return;
                    const cell = document.createElement('div');
                    cell.className = 'photo-pill';
                    const img = document.createElement('img');
                    img.alt = f.name;
                    const url = URL.createObjectURL(f);
                    img.src = url;
                    img.onload = function() { URL.revokeObjectURL(url); };
                    cell.appendChild(img);
                    dayPhotosPreview.appendChild(cell);
                });
            }
        });
    }
})();
