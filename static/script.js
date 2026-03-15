/* ============================================================
   Dijkstra Router — main script
   ============================================================ */

let map;
let routeLayer = null;
let markers = [];
let userLocationMarker = null;
let routePolyline = null;
let animatedRoutePolyline = null;
let _routeAbortController = null;  // cancel in-flight route requests

document.addEventListener('DOMContentLoaded', function () {

    /* ---- Map init ---- */
    map = L.map('map').setView([38.2, 23.7], 7);

    const lightTiles = L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
        { attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>', maxZoom: 19 }
    );
    const darkTiles = L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        { attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>', maxZoom: 19 }
    );
    window._lightTiles = lightTiles;
    window._darkTiles  = darkTiles;
    lightTiles.addTo(map);

    /* ---- Autocomplete geocoders ---- */
    setupAutocomplete('startLocation', 'startCoords', 'startAC');
    setupAutocomplete('endLocation',   'endCoords',   'endAC');

    /* ---- Form submit ---- */
    document.getElementById('routeForm').addEventListener('submit', function (e) {
        e.preventDefault();
        calculateRoute();
    });

    /* ---- Map click: set start then end ---- */
    map.on('click', function (e) {
        if (window.innerWidth <= 700) {
            const sidebar = document.getElementById('sidebar');
            if (sidebar) sidebar.classList.remove('active');
        }
        if (!document.getElementById('startCoords').value) {
            updateMarkerFromLatLng(e.latlng, 'start');
        } else if (!document.getElementById('endCoords').value) {
            updateMarkerFromLatLng(e.latlng, 'end');
        } else {
            document.getElementById('startCoords').value = document.getElementById('endCoords').value;
            document.getElementById('startLocation').value = document.getElementById('endLocation').value;
            updateMarkerFromLatLng(e.latlng, 'end');
        }
    });

    /* ---- Reset / back button ---- */
    document.getElementById('resetMapBtn').addEventListener('click', resetEverything);

    /* ---- Keyboard shortcuts ---- */
    document.addEventListener('keydown', function (e) {
        if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {
            e.preventDefault();
            resetEverything();
        } else if (e.key === 'Escape') {
            closeAllDropdowns();
        }
    });

    /* ---- Current location ---- */
    document.getElementById('useCurrentLocation').addEventListener('click', function () {
        if (!navigator.geolocation) {
            showToast('Ο εντοπισμός τοποθεσίας δεν υποστηρίζεται.', 'error');
            return;
        }
        showToast('Εντοπισμός τοποθεσίας...', 'info');
        navigator.geolocation.getCurrentPosition(
            function (pos) {
                const latlng = L.latLng(pos.coords.latitude, pos.coords.longitude);
                updateMarkerFromLatLng(latlng, 'start');
                map.setView(latlng, 14);
                showToast('Η τοποθεσία σας εντοπίστηκε!', 'success');
            },
            function (err) {
                showToast('Αδυναμία εντοπισμού: ' + err.message, 'error');
            }
        );
    });

    /* ---- Swap origin / destination ---- */
    document.getElementById('swapBtn').addEventListener('click', function () {
        const startLoc    = document.getElementById('startLocation').value;
        const endLoc      = document.getElementById('endLocation').value;
        const startCoords = document.getElementById('startCoords').value;
        const endCoords   = document.getElementById('endCoords').value;

        document.getElementById('startLocation').value = endLoc;
        document.getElementById('endLocation').value   = startLoc;
        document.getElementById('startCoords').value   = endCoords;
        document.getElementById('endCoords').value     = startCoords;

        updateClearBtn('clearStart', document.getElementById('startLocation').value);
        updateClearBtn('clearEnd',   document.getElementById('endLocation').value);

        // Swap map markers
        const startMarker = markers.find(m => m.type === 'start');
        const endMarker   = markers.find(m => m.type === 'end');
        if (startMarker) startMarker.type = 'end';
        if (endMarker)   endMarker.type   = 'start';

        // Clear stale route — coords have changed, old route is now wrong
        clearRouteFromMap();
        document.getElementById('routeInfo').style.display = 'none';
        document.getElementById('routeInstructions').style.display = 'none';

        showToast('Αφετηρία και προορισμός εναλλάχθηκαν.', 'info');
    });

    /* ---- Clear field buttons ---- */
    document.getElementById('clearStart').addEventListener('click', function () {
        clearField('startLocation', 'startCoords', 'clearStart', 'start');
    });
    document.getElementById('clearEnd').addEventListener('click', function () {
        clearField('endLocation', 'endCoords', 'clearEnd', 'end');
    });

    /* ---- Show/hide clear buttons as user types ---- */
    document.getElementById('startLocation').addEventListener('input', function () {
        updateClearBtn('clearStart', this.value);
    });
    document.getElementById('endLocation').addEventListener('input', function () {
        updateClearBtn('clearEnd', this.value);
    });

    /* ---- Transport mode tabs ---- */
    document.querySelectorAll('.t-tab').forEach(function (btn) {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.t-tab').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });

    /* ---- Theme toggle ---- */
    initThemeToggle();

    /* ---- Desktop sidebar collapse ---- */
    initSidebarCollapse();

    /* ---- Mobile sidebar toggle ---- */
    initSidebarToggle();

    /* ---- Close dropdowns on outside click ---- */
    document.addEventListener('click', function (e) {
        if (!e.target.closest('.dir-field-wrap')) {
            closeAllDropdowns();
        }
    });
});

/* ============================================================
   Autocomplete
   ============================================================ */

function setupAutocomplete(inputId, coordsId, acId) {
    const input     = document.getElementById(inputId);
    const coordsEl  = document.getElementById(coordsId);
    const dropdown  = document.getElementById(acId);
    let timer;

    input.addEventListener('input', function () {
        clearTimeout(timer);
        const q = this.value.trim();
        updateClearBtn(inputId === 'startLocation' ? 'clearStart' : 'clearEnd', q);

        if (q.length < 3) {
            closeDropdown(dropdown);
            return;
        }

        timer = setTimeout(function () {
            input.classList.add('loading');
            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=5&addressdetails=1`)
                .then(r => r.json())
                .then(function (data) {
                    input.classList.remove('loading');
                    if (!data || !data.length) {
                        closeDropdown(dropdown);
                        return;
                    }
                    renderDropdown(dropdown, data, function (item) {
                        const coords = [parseFloat(item.lon), parseFloat(item.lat)];
                        input.value      = item.display_name.split(',').slice(0, 2).join(', ');
                        coordsEl.value   = JSON.stringify(coords);
                        closeDropdown(dropdown);
                        updateMarker([parseFloat(item.lat), parseFloat(item.lon)],
                            inputId === 'startLocation' ? 'start' : 'end');
                        updateClearBtn(inputId === 'startLocation' ? 'clearStart' : 'clearEnd', input.value);
                        // Auto-focus destination after picking origin
                        if (inputId === 'startLocation') {
                            document.getElementById('endLocation').focus();
                        }
                    });
                })
                .catch(function () {
                    input.classList.remove('loading');
                    closeDropdown(dropdown);
                });
        }, 400);
    });

    input.addEventListener('focus', function () {
        // Close any other open dropdown first
        document.querySelectorAll('.ac-dropdown').forEach(function (d) {
            if (d !== dropdown) d.classList.remove('open');
        });
        if (dropdown.childElementCount > 0) {
            dropdown.classList.add('open');
        }
    });
}

function renderDropdown(dropdown, results, onSelect) {
    dropdown.innerHTML = '';

    if (!results || results.length === 0) {
        dropdown.innerHTML = '<div class="ac-empty">Δεν βρέθηκαν αποτελέσματα</div>';
        dropdown.classList.add('open');
        return;
    }

    results.forEach(function (item) {
        const parts   = item.display_name.split(',');
        const label   = parts[0].trim();
        const address = parts.slice(1, 3).join(',').trim();

        const el = document.createElement('div');
        el.className = 'ac-item';
        el.innerHTML = `
            <div class="ac-icon"><i class="fas fa-map-marker-alt"></i></div>
            <div class="ac-text">
                <div class="ac-name">${label}</div>
                ${address ? `<div class="ac-addr">${address}</div>` : ''}
            </div>`;
        el.addEventListener('mousedown', function (e) {
            e.preventDefault();
            onSelect(item);
        });
        dropdown.appendChild(el);
    });
    dropdown.classList.add('open');
}

function closeDropdown(dropdown) {
    dropdown.classList.remove('open');
}

function closeAllDropdowns() {
    document.querySelectorAll('.ac-dropdown').forEach(d => d.classList.remove('open'));
}

/* ============================================================
   Field helpers
   ============================================================ */

function updateClearBtn(btnId, value) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    if (value && value.length > 0) {
        btn.classList.add('visible');
    } else {
        btn.classList.remove('visible');
    }
}

function clearField(inputId, coordsId, btnId, type) {
    document.getElementById(inputId).value  = '';
    document.getElementById(coordsId).value = '';
    updateClearBtn(btnId, '');
    // Remove map marker
    markers = markers.filter(function (m) {
        if (m.type === type) { map.removeLayer(m.marker); return false; }
        return true;
    });
}

/* ============================================================
   Reverse geocode + marker on map click
   ============================================================ */

function updateMarkerFromLatLng(latlng, type) {
    const inputId  = type === 'start' ? 'startLocation' : 'endLocation';
    const coordsId = type === 'start' ? 'startCoords'   : 'endCoords';
    const btnId    = type === 'start' ? 'clearStart'    : 'clearEnd';

    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latlng.lat}&lon=${latlng.lng}`)
        .then(r => r.json())
        .then(function (data) {
            if (data && data.display_name) {
                const parts = data.display_name.split(',');
                document.getElementById(inputId).value = parts.slice(0, 2).join(', ');
            }
        })
        .catch(function () {})
        .finally(function () {
            document.getElementById(coordsId).value = JSON.stringify([latlng.lng, latlng.lat]);
            updateMarker([latlng.lat, latlng.lng], type);
            updateClearBtn(btnId, document.getElementById(inputId).value || '?');
        });
}

/* ============================================================
   Map markers
   ============================================================ */

function updateMarker(latlng, type) {
    markers = markers.filter(function (m) {
        if (m.type === type) { map.removeLayer(m.marker); return false; }
        return true;
    });

    const icon = type === 'start'
        ? L.divIcon({ className: '', html: '<div class="gm-dot-start"></div>', iconSize: [14, 14], iconAnchor: [7, 7] })
        : L.divIcon({ className: '', html: '<div class="gm-pin-end"></div>',   iconSize: [24, 30], iconAnchor: [12, 28] });

    const marker = L.marker(latlng, { icon, riseOnHover: true }).addTo(map);
    markers.push({ marker, type });

    if (markers.length === 2) {
        const bounds = L.latLngBounds(markers.map(m => m.marker.getLatLng()));
        map.fitBounds(bounds, { padding: [60, 60] });
    } else {
        map.setView(latlng, 13);
    }
}

/* ============================================================
   Route calculation
   ============================================================ */

async function calculateRoute() {
    const startInput = document.getElementById('startCoords');
    const endInput   = document.getElementById('endCoords');

    if (!startInput.value || !endInput.value) {
        showToast('Παρακαλώ επιλέξτε αφετηρία και προορισμό.', 'error');
        return;
    }

    let startCoords, endCoords;
    try {
        startCoords = JSON.parse(startInput.value);
        endCoords   = JSON.parse(endInput.value);
    } catch (_) {
        showToast('Άκυρες συντεταγμένες. Επιλέξτε τοποθεσίες από τη λίστα.', 'error');
        return;
    }

    // Cancel any previous in-flight request
    if (_routeAbortController) {
        _routeAbortController.abort();
    }
    _routeAbortController = new AbortController();
    const signal = _routeAbortController.signal;

    clearRouteFromMap();

    const submitBtn  = document.querySelector('.search-action .route-btn');
    const submitText = document.getElementById('submitBtnText');
    if (submitBtn) submitBtn.disabled = true;
    if (submitText) submitText.innerHTML = '<span class="loader"></span> Υπολογισμός...';
    showToast('Λήψη δεδομένων χάρτη, παρακαλώ περιμένετε…', 'info');

    document.getElementById('routeInfo').style.display = 'none';
    document.getElementById('routeInstructions').style.display = 'none';

    const routeBody = JSON.stringify({ start: startCoords, end: endCoords, type: 'driving' });

    async function postRoute(url) {
        const r = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: routeBody,
            signal
        });
        return r.json();
    }

    try {
        let data;
        try {
            data = await postRoute('/route_with_traffic_visualization');
        } catch (_) {
            data = await postRoute('/route');
        }

        if (data.error) throw new Error(data.error);
        if (data.success === false) throw new Error(data.message || 'Δεν βρέθηκε διαδρομή');

        window.lastRouteData = data;
        const routeData = data.route;
        const isApprox  = data.isApproximate || false;

        if (!routeData || !routeData.geometry || !Array.isArray(routeData.geometry)) {
            throw new Error('Δεν κατέστη δυνατή η εύρεση διαδρομής. Δοκιμάστε σημεία κοντά σε δρόμους.');
        }

        // Draw route
        if (routeData.traffic_segments && routeData.traffic_segments.length > 0) {
            drawTrafficColoredRoute(routeData.traffic_segments);
            addTrafficLegend(data.traffic_legend);
        } else {
            const coords = routeData.geometry.map(c => [c[1], c[0]]);
            routePolyline = L.polyline(coords, {
                color:     isApprox ? '#FF6B6B' : '#1a73e8',
                weight:    6,
                opacity:   0.92,
                lineCap:   'round',
                lineJoin:  'round',
                dashArray: isApprox ? '14, 10' : null,
                className: 'leaflet-polyline-gradient'
            }).addTo(map);
            routeLayer = routePolyline;
            map.fitBounds(routePolyline.getBounds(), { padding: [60, 60] });
        }

        if (isApprox) {
            showToast('Προσοχή: Προσεγγιστική διαδρομή — ίσως να μην ακολουθεί το οδικό δίκτυο.', 'warning');
        }

        const distance = routeData.distance_km || routeData.distance;
        const duration = routeData.duration_seconds ?? routeData.duration ?? 0;

        displayRouteInfo(distance, duration, isApprox);

        const steps = routeData.steps && routeData.steps.length > 0
            ? routeData.steps
            : window.routeSteps;
        if (steps) showRouteInstructions(steps);
        window.routeSteps = routeData.steps;

        showToast('Η διαδρομή υπολογίστηκε!', 'success');
    } catch (err) {
        if (err.name !== 'AbortError') {
            showToast('Σφάλμα: ' + err.message, 'error');
        }
    } finally {
        if (submitBtn) submitBtn.disabled = false;
        if (submitText) submitText.innerHTML = 'Εύρεση Διαδρομής';
    }
}

/* ============================================================
   Display route info (Google Maps style)
   ============================================================ */

function displayRouteInfo(distance, durationSec, isApprox) {
    const routeInfoDiv = document.getElementById('routeInfo');
    if (!routeInfoDiv) return;

    const hours   = Math.floor(durationSec / 3600);
    const minutes = Math.floor((durationSec % 3600) / 60);
    const timeStr = hours > 0 ? `${hours} ώρ. ${minutes} λεπ.` : `${minutes} λεπτά`;

    const distStr = distance ? `${parseFloat(distance).toFixed(1)} χλμ` : '';

    routeInfoDiv.innerHTML = `
        <div class="route-summary fade-in">
            <div class="route-time-row">
                <span class="route-time">${timeStr}</span>
                <span class="route-dist">${distStr}</span>
            </div>
            <div class="traffic-badge free">
                <span class="badge-dot"></span> Κανονική κίνηση
            </div>
            ${isApprox ? `<div class="route-warning"><i class="fas fa-exclamation-triangle"></i> Προσεγγιστική διαδρομή</div>` : ''}
            <div class="route-action-bar">
                <button class="btn-start" onclick="showToast('Λειτουργία πλοήγησης σύντομα διαθέσιμη!', \'info\')">
                    <i class="fas fa-location-arrow"></i> Εκκίνηση
                </button>
                <button class="btn-icon" title="Κοινοποίηση" onclick="showToast('Κοινοποίηση σύντομα!', \'info\')">
                    <i class="fas fa-share-alt"></i>
                </button>
            </div>
        </div>`;

    routeInfoDiv.style.display = 'block';
    const hint = document.getElementById('emptyHint');
    if (hint) hint.style.display = 'none';
}

/* ============================================================
   Turn-by-turn instructions
   ============================================================ */

function getStepIcon(instruction) {
    if (!instruction) return 'fa-arrow-up';
    const t = instruction.toLowerCase();
    // Greek 8-direction labels from backend
    if (t.includes('βορειοανατολ'))  return 'fa-turn-right';
    if (t.includes('νοτιοανατολ'))   return 'fa-turn-right';
    if (t.includes('βορειοδυτ'))     return 'fa-turn-left';
    if (t.includes('νοτιοδυτ'))      return 'fa-turn-left';
    if (t.includes('ανατολ'))        return 'fa-arrow-right';
    if (t.includes('δυτ'))           return 'fa-arrow-left';
    if (t.includes('νότια'))         return 'fa-arrow-down';
    if (t.includes('βόρεια') || t.includes('ευθεία') || t.includes('συνέχεια')) return 'fa-arrow-up';
    // Generic keywords
    if (t.includes('δεξιά')  || t.includes('right'))        return 'fa-turn-right';
    if (t.includes('αριστερά') || t.includes('left'))       return 'fa-turn-left';
    if (t.includes('φτάσατε') || t.includes('arrive') || t.includes('destination')) return 'fa-flag-checkered';
    if (t.includes('αναχωρ') || t.includes('depart') || t.includes('head'))         return 'fa-circle-dot';
    if (t.includes('στρογγυλ') || t.includes('roundabout') || t.includes('κυκλ'))   return 'fa-rotate-right';
    if (t.includes('συγχωνε') || t.includes('merge'))       return 'fa-code-merge';
    if (t.includes('έξοδο')  || t.includes('exit'))         return 'fa-right-from-bracket';
    if (t.includes('continue'))                              return 'fa-arrow-up';
    return 'fa-arrow-up';
}

function showRouteInstructions(steps) {
    const el = document.getElementById('routeInstructions');
    if (!el) return;

    if (!steps || !Array.isArray(steps) || steps.length === 0) {
        el.style.display = 'none';
        return;
    }

    const safeSteps = steps.filter(s => s && s.instruction);
    if (safeSteps.length === 0) { el.style.display = 'none'; return; }

    const html = safeSteps.map(function (s) {
        const icon = getStepIcon(s.instruction);
        const dist = s.distance ? formatStepDistance(s.distance) : '';
        const dur  = (s.duration || s.time) ? formatDuration(s.duration || s.time) : '';
        return `
            <div class="step-item">
                <div class="step-icon"><i class="fas ${icon}"></i></div>
                <div class="step-content">
                    <div class="step-instruction">${s.instruction}</div>
                    ${(dist || dur) ? `<div class="step-meta">${dist ? `<span class="step-dist">${dist}</span>` : ''}${dur ? `<span class="step-dur">${dur}</span>` : ''}</div>` : ''}
                </div>
            </div>`;
    }).join('');

    el.innerHTML = `<div class="steps-header">Οδηγίες</div>${html}`;
    el.style.display = 'block';
}

function formatDuration(sec) {
    if (!sec) return '';
    const m = Math.round(sec / 60);
    if (m < 1) return '<1 λεπ.';
    if (m < 60) return `${m} λεπ.`;
    const h = Math.floor(m / 60);
    const rem = m % 60;
    return rem > 0 ? `${h} ώρ. ${rem} λεπ.` : `${h} ώρ.`;
}

function formatStepDistance(distKm) {
    if (!distKm) return '';
    const km = parseFloat(distKm);
    if (km < 0.001) return '';
    if (km < 1) return `${Math.round(km * 1000)} μ.`;
    return `${km.toFixed(1)} χλμ`;
}

/* ============================================================
   Traffic route drawing
   ============================================================ */

function drawTrafficColoredRoute(trafficSegments) {
    clearRouteFromMap();
    routeLayer = L.layerGroup().addTo(map);

    trafficSegments.forEach(function (segment) {
        if (segment.coordinates && segment.coordinates.length >= 2) {
            const coords = segment.coordinates.map(c => [c[1], c[0]]);
            const poly   = L.polyline(coords, {
                color:    segment.color,
                weight:   8,
                opacity:  0.95,
                lineCap:  'round',
                lineJoin: 'round'
            });
            poly.bindTooltip(
                `<strong>Κίνηση:</strong> ${getTrafficLevelText(segment.traffic_level)}<br>
                 <strong>Καθυστέρηση:</strong> +${(segment.delay_factor * 100 - 100).toFixed(0)}%`,
                { sticky: true, className: 'traffic-tooltip' }
            );
            routeLayer.addLayer(poly);
        }
    });

    if (routeLayer.getLayers().length > 0) {
        const group = new L.featureGroup(routeLayer.getLayers());
        map.fitBounds(group.getBounds(), { padding: [60, 60] });
    }
}

function addTrafficLegend(trafficLegend) {
    if (window.trafficLegendControl) {
        map.removeControl(window.trafficLegendControl);
        window.trafficLegendControl = null;
    }
    if (!trafficLegend) return;

    const legendHtml = `
        <div class="traffic-legend">
            <h4>Κατάσταση Κίνησης</h4>
            ${Object.entries(trafficLegend).map(([, info]) => `
                <div class="legend-item">
                    <span class="legend-color" style="background:${info.color}"></span>
                    <span>${info.description}</span>
                </div>`).join('')}
        </div>`;

    const ctrl = L.control({ position: 'bottomright' });
    ctrl.onAdd = function () {
        const div = L.DomUtil.create('div', 'legend-control');
        div.innerHTML = legendHtml;
        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.disableScrollPropagation(div);
        return div;
    };
    ctrl.addTo(map);
    window.trafficLegendControl = ctrl;
}

function getTrafficLevelText(level) {
    const m = {
        free_flow: 'Ελεύθερη κίνηση',
        light:     'Ελαφριά κίνηση',
        moderate:  'Μέτρια κίνηση',
        heavy:     'Βαριά κίνηση',
        unknown:   'Άγνωστη'
    };
    return m[level] || 'Άγνωστη';
}

/* ============================================================
   Reset everything
   ============================================================ */

function clearRouteFromMap() {
    if (routePolyline) { map.removeLayer(routePolyline); routePolyline = null; }
    if (animatedRoutePolyline) { map.removeLayer(animatedRoutePolyline); animatedRoutePolyline = null; }
    if (routeLayer) {
        if (routeLayer.clearLayers) routeLayer.clearLayers();
        map.removeLayer(routeLayer);
        routeLayer = null;
    }
    if (window.trafficLegendControl) {
        map.removeControl(window.trafficLegendControl);
        window.trafficLegendControl = null;
    }
}

function resetEverything() {
    // Clear inputs
    ['startLocation', 'endLocation'].forEach(id => { document.getElementById(id).value = ''; });
    ['startCoords',   'endCoords'  ].forEach(id => { document.getElementById(id).value = ''; });
    updateClearBtn('clearStart', '');
    updateClearBtn('clearEnd',   '');
    closeAllDropdowns();

    // Clear markers
    markers.forEach(function (m) {
        if (m && m.marker) map.removeLayer(m.marker);
    });
    markers = [];

    if (userLocationMarker) { map.removeLayer(userLocationMarker); userLocationMarker = null; }

    // Clear route
    clearRouteFromMap();

    // Hide panels, restore hint
    const ri = document.getElementById('routeInfo');
    if (ri) { ri.style.display = 'none'; ri.innerHTML = ''; }
    const rin = document.getElementById('routeInstructions');
    if (rin) { rin.style.display = 'none'; rin.innerHTML = ''; }
    const hint = document.getElementById('emptyHint');
    if (hint) hint.style.display = '';

    // Reset map view
    map.setView([38.2, 23.7], 7);

    // Reset globals
    window.lastRouteData = null;
    window.routeSteps    = null;

    // Reset button
    const text = document.getElementById('submitBtnText');
    if (text) text.innerHTML = 'Εύρεση Διαδρομής';

    document.getElementById('startLocation').focus();
    showToast('Έτοιμο για νέα αναζήτηση.', 'success');
}

/* ============================================================
   Toast notifications
   ============================================================ */

function showToast(message, type) {
    type = type || 'info';
    const container = document.querySelector('.toast-container');
    const toast     = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = { success: 'check-circle', error: 'exclamation-circle', warning: 'exclamation-triangle', info: 'info-circle' };
    toast.innerHTML = `<i class="fas fa-${icons[type] || 'info-circle'}"></i><span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(function () {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity .3s';
        setTimeout(function () {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 320);
    }, 3000);
}

/* ============================================================
   Theme toggle
   ============================================================ */

function initThemeToggle() {
    const btn  = document.getElementById('themeToggle');
    const icon = btn.querySelector('i');

    const saved     = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');

    applyTheme(theme, icon);

    btn.addEventListener('click', function () {
        const current  = document.documentElement.getAttribute('data-theme');
        const newTheme = current === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme, icon);
        localStorage.setItem('theme', newTheme);
        showToast(newTheme === 'dark' ? 'Σκοτεινό θέμα' : 'Φωτεινό θέμα', 'info');
    });
}

function applyTheme(theme, icon) {
    document.documentElement.setAttribute('data-theme', theme);
    if (icon) {
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
    if (map && window._lightTiles && window._darkTiles) {
        if (theme === 'dark') {
            if (map.hasLayer(window._lightTiles)) map.removeLayer(window._lightTiles);
            if (!map.hasLayer(window._darkTiles))  window._darkTiles.addTo(map);
        } else {
            if (map.hasLayer(window._darkTiles))  map.removeLayer(window._darkTiles);
            if (!map.hasLayer(window._lightTiles)) window._lightTiles.addTo(map);
        }
        map.invalidateSize();
    }
}

/* ============================================================
   Desktop sidebar collapse/expand
   ============================================================ */

function initSidebarCollapse() {
    const btn = document.getElementById('sidebarCollapseBtn');
    if (!btn) return;

    btn.addEventListener('click', function () {
        const collapsed = document.body.classList.toggle('sidebar-collapsed');
        btn.title = collapsed ? 'Εμφάνιση πλαισίου' : 'Απόκρυψη πλαισίου';
        // Let CSS transition finish, then tell Leaflet the map resized
        setTimeout(function () {
            if (map) map.invalidateSize({ animate: false });
        }, 300);
    });
}

/* ============================================================
   Mobile sidebar
   ============================================================ */

function initSidebarToggle() {
    const btn     = document.getElementById('toggleSidebar');
    const sidebar = document.getElementById('sidebar');

    btn.addEventListener('click', function () {
        const open = sidebar.classList.toggle('active');
        document.body.classList.toggle('sidebar-open', open);
        const icon = btn.querySelector('i');
        icon.className = open ? 'fas fa-times' : 'fas fa-bars';
        setTimeout(function () { if (map) map.invalidateSize(); }, 320);
    });

    // Close on map click (mobile)
    map.on('click', function () {
        if (window.innerWidth <= 700 && sidebar.classList.contains('active')) {
            sidebar.classList.remove('active');
            document.body.classList.remove('sidebar-open');
            const icon = btn.querySelector('i');
            if (icon) icon.className = 'fas fa-bars';
        }
    });

    window.addEventListener('resize', function () {
        if (window.innerWidth > 700) {
            sidebar.classList.remove('active');
            document.body.classList.remove('sidebar-open');
            const icon = btn.querySelector('i');
            if (icon) icon.className = 'fas fa-bars';
        }
        if (map) map.invalidateSize();
    });
}

/* ============================================================
   Animated route drawing (utility)
   ============================================================ */

function animateRoute(coords) {
    if (routePolyline) { map.removeLayer(routePolyline); routePolyline = null; }
    let i = 1;
    routePolyline = L.polyline([coords[0]], {
        color: '#1a73e8',
        weight: 6,
        opacity: 0.92,
        lineCap: 'round',
        lineJoin: 'round'
    }).addTo(map);
    const timer = setInterval(function () {
        if (i >= coords.length) { clearInterval(timer); return; }
        routePolyline.addLatLng(coords[i++]);
    }, 20);
}

/* ============================================================
   User location marker
   ============================================================ */

function showUserLocation() {
    if (!navigator.geolocation) return showToast('Δεν υποστηρίζεται το geolocation.', 'error');
    navigator.geolocation.getCurrentPosition(function (pos) {
        const latlng = [pos.coords.latitude, pos.coords.longitude];
        if (userLocationMarker) map.removeLayer(userLocationMarker);
        userLocationMarker = L.marker(latlng, {
            icon: L.divIcon({ className: 'user-location-marker' }),
            zIndexOffset: 1000
        }).addTo(map);
        map.setView(latlng, 15, { animate: true });
    }, function () {
        showToast('Αποτυχία εύρεσης τοποθεσίας.', 'error');
    });
}

/* ============================================================
   Clipboard helpers
   ============================================================ */

document.addEventListener('click', function (e) {
    if (e.target.closest('#copyStartCoords')) {
        navigator.clipboard.writeText(document.getElementById('startCoords').value);
        showToast('Αντιγράφηκε η αφετηρία!', 'success');
    } else if (e.target.closest('#copyEndCoords')) {
        navigator.clipboard.writeText(document.getElementById('endCoords').value);
        showToast('Αντιγράφηκε ο προορισμός!', 'success');
    }
});
