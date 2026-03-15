let map;
let routeLayer;
let markers = [];
let searchTimeout;

document.addEventListener('DOMContentLoaded', function() {
    // αρχικοποίηση χάρτη
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
    
    // αναζήτηση για εισόδους
    setupGeocoder('startLocation', 'startCoords');
    setupGeocoder('endLocation', 'endCoords');
    
    // Handle form submission
    document.getElementById('routeForm').addEventListener('submit', function(e) {
        e.preventDefault();
        calculateRoute();
    });
    
    // Handle map clicks to set markers
    map.on('click', function(e) {
        // Check if we're setting start or end point
        if (!document.getElementById('startCoords').value) {
            updateMarkerFromLatLng(e.latlng, 'start');
        } else if (!document.getElementById('endCoords').value) {
            updateMarkerFromLatLng(e.latlng, 'end');
        } else {
            // If both are set, update the start and move the end to start
            const endCoords = JSON.parse(document.getElementById('endCoords').value);
            document.getElementById('startCoords').value = document.getElementById('endCoords').value;
            document.getElementById('startLocation').value = document.getElementById('endLocation').value;
            
            // Update end with new coords
            updateMarkerFromLatLng(e.latlng, 'end');
        }
    });
    
    // Handle refresh/reset button
    document.getElementById('resetMapBtn').addEventListener('click', function() {
        resetEverything();
    });
    
    // Handle keyboard shortcuts for reset
    document.addEventListener('keydown', function(e) {
        // Ctrl+R or F5 for reset (prevent default browser refresh)
        if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {
            e.preventDefault();
            resetEverything();
        }
        // Escape key for reset
        else if (e.key === 'Escape') {
            resetEverything();
        }
    });
    
    // Handle current location button
    document.getElementById('useCurrentLocation').addEventListener('click', function() {
        if (navigator.geolocation) {
            showToast('Εντοπισμός τοποθεσίας...', 'info');
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const latlng = L.latLng(position.coords.latitude, position.coords.longitude);
                    updateMarkerFromLatLng(latlng, 'start');
                    map.setView(latlng, 14);
                    showToast('Η τοποθεσία σας εντοπίστηκε!', 'success');
                },
                function(error) {
                    console.error('Error getting location:', error);
                    showToast('Αδυναμία εντοπισμού τοποθεσίας. ' + error.message, 'error');
                }
            );
        } else {
            showToast('Ο εντοπισμός τοποθεσίας δεν υποστηρίζεται από τον περιηγητή σας.', 'error');
        }
    });
    
    // Handle reset map button
    document.getElementById('resetMapBtn').addEventListener('click', function() {
        // Remove main route polyline
        if (typeof routePolyline !== 'undefined' && routePolyline) {
            map.removeLayer(routePolyline);
            routePolyline = null;
        }
        // Remove animated route polyline if exists
        if (typeof animatedRoutePolyline !== 'undefined' && animatedRoutePolyline) {
            map.removeLayer(animatedRoutePolyline);
            animatedRoutePolyline = null;
        }
        // Remove ALL polylines with specific class (e.g. gradient)
        map.eachLayer(function(layer) {
            if (layer instanceof L.Polyline && layer.options.className && layer.options.className.includes('leaflet-polyline-gradient')) {
                map.removeLayer(layer);
            }
        });
        // Remove markers
        if (typeof markers !== 'undefined' && Array.isArray(markers)) {
            markers.forEach(m => map.removeLayer(m.marker));
            markers = [];
        }
        // Ασφαλής πρόσβαση σε στοιχεία που μπορεί να μην υπάρχουν
        const routeInfo = document.getElementById('routeInfo');
        if (routeInfo) routeInfo.style.display = 'none';
        
        const routeInstructions = document.getElementById('routeInstructions');
        if (routeInstructions) routeInstructions.innerHTML = '';
        
        // Clear start/end fields - με έλεγχο ασφαλείας
        const startLocationEl = document.getElementById('startLocation');
        const endLocationEl = document.getElementById('endLocation');
        const startCoordsEl = document.getElementById('startCoords');
        const endCoordsEl = document.getElementById('endCoords');
        
        if (startLocationEl) startLocationEl.value = '';
        if (endLocationEl) endLocationEl.value = '';
        if (startCoordsEl) startCoordsEl.value = '';
        if (endCoordsEl) endCoordsEl.value = '';
        // Remove user location marker if exists
        if (typeof userLocationMarker !== 'undefined' && userLocationMarker) {
            map.removeLayer(userLocationMarker);
            userLocationMarker = null;
        }
        showToast('Ο χάρτης καθαρίστηκε.', 'success');
    });
    
    // Handle toggle sidebar for mobile
    document.getElementById('toggleSidebar').addEventListener('click', function() {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) sidebar.classList.toggle('active');
    });
    
    // Add animation to elements
    animateElements();
    
    // Dark mode functionality
    function initThemeToggle() {
        const themeToggleBtn = document.getElementById('themeToggle');
        const themeIcon = themeToggleBtn.querySelector('i');
        
        // Check for saved theme preference or use preferred color scheme
        const savedTheme = localStorage.getItem('theme');
        const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
        
        if (savedTheme === 'dark' || (!savedTheme && prefersDarkScheme.matches)) {
            document.documentElement.setAttribute('data-theme', 'dark');
            themeIcon.classList.replace('fa-moon', 'fa-sun');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            themeIcon.classList.replace('fa-sun', 'fa-moon');
        }
        
        // Toggle theme on button click
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            let newTheme;
            
            if (currentTheme === 'light') {
                newTheme = 'dark';
                themeIcon.classList.replace('fa-moon', 'fa-sun');
            } else {
                newTheme = 'light';
                themeIcon.classList.replace('fa-sun', 'fa-moon');
            }
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Swap tile layers for dark/light mode
            if (map && window._lightTiles && window._darkTiles) {
                if (newTheme === 'dark') {
                    map.removeLayer(window._lightTiles);
                    window._darkTiles.addTo(map);
                } else {
                    map.removeLayer(window._darkTiles);
                    window._lightTiles.addTo(map);
                }
                map.invalidateSize();
            }
            
            // Show toast notification
            showToast(`${newTheme.charAt(0).toUpperCase() + newTheme.slice(1)} mode enabled`, 'info');
        });
    }

    // Responsive sidebar toggle for mobile
    function initSidebarToggle() {
        const toggleSidebarBtn = document.getElementById('toggleSidebar');
        const sidebar = document.getElementById('sidebar');
        
        toggleSidebarBtn.addEventListener('click', () => {
            if (sidebar) sidebar.classList.toggle('active');
            
            // Update button icon
            const icon = toggleSidebarBtn?.querySelector('i');
            if (sidebar && sidebar.classList.contains('active')) {
                icon?.classList.replace('fa-bars', 'fa-times');
            } else {
                icon?.classList.replace('fa-times', 'fa-bars');
            }
        });
        
        // Close sidebar when clicking on map in mobile view
        if (window.innerWidth < 768) {
            map.on('click', () => {
                if (sidebar) sidebar.classList.remove('active');
                const icon = toggleSidebarBtn?.querySelector('i');
                if (icon) {
                    icon.classList.replace('fa-times', 'fa-bars');
                }
            });
        }
        
        // Handle resize events
        window.addEventListener('resize', () => {
            if (window.innerWidth >= 768 && sidebar) {
                sidebar.classList.remove('active');
                const icon = toggleSidebarBtn?.querySelector('i');
                if (icon) {
                    icon.classList.replace('fa-times', 'fa-bars');
                }
            }
            
            // Invalidate map size when resizing
            if (map) {
                map.invalidateSize();
            }
        });
    }

    initThemeToggle();
    initSidebarToggle();
    
    // --- Enhance calculateRoute with better error messages ---
    const originalCalculateRoute = calculateRoute;
    calculateRoute = function() {
        try {
            originalCalculateRoute();
        } catch (e) {
            console.error('Error in calculateRoute:', e);
            showToast('Σφάλμα υπολογισμού διαδρομής: ' + e.message, 'error');
        }
    };
    // Enhanced toast for error messages
    const oldShowToast = showToast;
    showToast = function(message, type) {
        oldShowToast(message, type);
    };

    // --- Sidebar Animation ---
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.add('fade-in');
    }
});

function setupGeocoder(inputId, coordsId) {
    const input = document.getElementById(inputId);
    const coordsInput = document.getElementById(coordsId);
    
    input.addEventListener('input', function() {
        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        // Wait for user to stop typing
        searchTimeout = setTimeout(() => {
            const query = input.value;
            if (query.length < 3) return;
            
            // Show loading state
            input.classList.add('loading');
            
            // Use Nominatim API for geocoding
            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=5`)
                .then(response => response.json())
                .then(data => {
                    input.classList.remove('loading');
                    
                    if (data && data.length > 0) {
                        const location = data[0];
                        const coords = [parseFloat(location.lon), parseFloat(location.lat)];
                        coordsInput.value = JSON.stringify(coords);
                        
                        // Update marker
                        updateMarker([parseFloat(location.lat), parseFloat(location.lon)], inputId === 'startLocation' ? 'start' : 'end');
                        
                        // Show success toast
                        showToast(`Η τοποθεσία "${location.display_name.split(',')[0]}" βρέθηκε!`, 'success');
                    } else {
                        showToast('Δεν βρέθηκε η τοποθεσία. Δοκιμάστε ξανά.', 'error');
                    }
                })
                .catch(error => {
                    input.classList.remove('loading');
                    console.error('Error searching location:', error);
                    showToast('Σφάλμα αναζήτησης τοποθεσίας', 'error');
                });
        }, 500);
    });
}

function updateMarkerFromLatLng(latlng, type) {
    // Reverse geocode to get location name
    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latlng.lat}&lon=${latlng.lng}`)
        .then(response => response.json())
        .then(data => {
            if (data && data.display_name) {
                // Update input field with location name
                const inputId = type === 'start' ? 'startLocation' : 'endLocation';
                document.getElementById(inputId).value = data.display_name.split(',')[0];
                
                // Update coords input
                const coordsId = type === 'start' ? 'startCoords' : 'endCoords';
                document.getElementById(coordsId).value = JSON.stringify([latlng.lng, latlng.lat]);
                
                // Update marker
                updateMarker([latlng.lat, latlng.lng], type);
            }
        })
        .catch(error => {
            console.error('Error in reverse geocoding:', error);
            // Still update marker and coords even if reverse geocoding fails
            const coordsId = type === 'start' ? 'startCoords' : 'endCoords';
            document.getElementById(coordsId).value = JSON.stringify([latlng.lng, latlng.lat]);
            updateMarker([latlng.lat, latlng.lng], type);
        });
}

function updateMarker(latlng, type) {
    // Remove existing marker of this type
    markers = markers.filter(m => {
        if (m.type === type) {
            map.removeLayer(m.marker);
            return false;
        }
        return true;
    });

    // Google Maps-style icon
    const icon = type === 'start'
        ? L.divIcon({ className: '', html: '<div class="gm-dot-start"></div>', iconSize: [14,14], iconAnchor: [7,7] })
        : L.divIcon({ className: '', html: '<div class="gm-pin-end"></div>',  iconSize: [24,30], iconAnchor: [12,28] });

    const marker = L.marker(latlng, {icon: icon, riseOnHover: true}).addTo(map);
    
    // Add popup with location info
    const locationInput = document.getElementById(type === 'start' ? 'startLocation' : 'endLocation').value;
    if (locationInput) {
        marker.bindPopup(`<b>${type === 'start' ? 'Αφετηρία' : 'Προορισμός'}</b><br>${locationInput}`).openPopup();
    }
    
    markers.push({marker, type});
    
    // Fit bounds if we have both markers
    if (markers.length === 2) {
        const bounds = L.latLngBounds(markers.map(m => m.marker.getLatLng()));
        map.fitBounds(bounds, {padding: [50, 50]});
    } else {
        map.setView(latlng, 12);
    }
}

function calculateRoute() {
    const startInput = document.getElementById('startCoords');
    const endInput = document.getElementById('endCoords');
    
    if (!startInput.value || !endInput.value) {
        showToast('Παρακαλώ επιλέξτε αφετηρία και προορισμό', 'error');
        return;
    }
    
    const startCoords = JSON.parse(startInput.value);
    const endCoords = JSON.parse(endInput.value);
    
    // Clear existing route
    if (routeLayer) {
        map.removeLayer(routeLayer);
    }
    
    // Show loading state
    const submitButton = document.getElementById('routeForm').querySelector('button');
    const originalBtnText = document.getElementById('submitBtnText').innerHTML;
    submitButton.disabled = true;
    document.getElementById('submitBtnText').innerHTML = '<span class="loader"></span> Υπολογισμός...';
    
    // Hide previous route info
    document.getElementById('routeInfo').style.display = 'none';
    
    // Try new traffic visualization endpoint, fallback to old one
    const endpoint = '/route_with_traffic_visualization';
    
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            start: startCoords,
            end: endCoords,
            type: 'driving'
        })
    }).catch(error => {
        // If new endpoint fails, try the old one
        console.log('Falling back to old endpoint:', error);
        return fetch('/route', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                start: startCoords,
                end: endCoords,
                type: 'driving'
            })
        });
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Σφάλμα δικτύου');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Store route data globally
        window.lastRouteData = data;
        
        // Create route line from coordinates with animation
        const routeData = data.route;
        
        // Έλεγχος αν υπάρχει το routeData και η γεωμετρία του
        if (!routeData || !routeData.geometry || !Array.isArray(routeData.geometry)) {
            console.error('Invalid route data received:', routeData);
            showToast('Σφάλμα: Λήφθηκαν μη έγκυρα δεδομένα διαδρομής', 'error');
            return; // Επιστρέφουμε αν δεν υπάρχουν έγκυρα δεδομένα
        }
        
        const isApproximate = data.isApproximate || false;
        
        // Draw colored route segments based on traffic
        if (routeData.traffic_segments && routeData.traffic_segments.length > 0) {
            // Draw traffic-colored segments
            drawTrafficColoredRoute(routeData.traffic_segments);
            
            // Add traffic legend
            addTrafficLegend(data.traffic_legend);
            
            // Skip the old polyline code since we're using traffic segments
        } else {
            // Fallback to regular route drawing
            const routeCoords = routeData.geometry.map(coord => [coord[1], coord[0]]);
            
            let routePolyline = L.polyline(routeCoords, {
                color: isApproximate ? '#FF6B6B' : '#0078FF',
                weight: 7,
                opacity: 0.93,
                lineCap: 'round',
                lineJoin: 'round',
                dashArray: isApproximate ? '15, 10' : null
            }).addTo(map);
            
            routeLayer = routePolyline;
            
            // Add tooltip for regular route
            const distance = routeData.distance_km || routeData.distance;
            const distanceText = distance ? (distance + ' χλμ') : 'Διαδρομή';
            
            routePolyline.bindTooltip(
                distanceText,
                {permanent: false, direction: 'top', className: 'route-tooltip'}
            );
        }
        
        // Αν είναι προσεγγιστική διαδρομή, προσθέτουμε προειδοποίηση
        if (isApproximate) {
            showToast('Προσοχή: Αυτή είναι μια προσεγγιστική διαδρομή και ίσως να μην ακολουθεί το οδικό δίκτυο', 'warning');
            
            // Προσθήκη ένδειξης στην πληροφορία διαδρομής
            const routeInfoEl = document.getElementById('routeInfo');
            if (routeInfoEl) {
                const warningEl = document.createElement('div');
                warningEl.className = 'route-warning';
                warningEl.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Προσεγγιστική διαδρομή';
                routeInfoEl.insertBefore(warningEl, routeInfoEl.firstChild);
            }
        }
        
        // Tooltip with distance - only for regular routes (not traffic segments)
        if (!routeData.traffic_segments && routeLayer && routeLayer.bindTooltip) {
            const distanceEl = document.getElementById('distance');
            const distanceText = distanceEl ? (distanceEl.textContent + ' χλμ') : 'Διαδρομή';
            
            routeLayer.bindTooltip(
                distanceText,
                {permanent: false, direction: 'top', className: 'route-tooltip'}
            );
        }
        // Highlight on info hover - με έλεγχο ασφαλείας
        const routeDetailsEl = document.querySelector('.route-details');
        if (routeDetailsEl && routeLayer && !routeData.traffic_segments) {
            routeDetailsEl.addEventListener('mouseenter', () => {
                if (routeLayer && routeLayer.setStyle) {
                    routeLayer.setStyle({className:'leaflet-polyline-gradient leaflet-polyline-highlight'});
                }
            });
            
            routeDetailsEl.addEventListener('mouseleave', () => {
                if (routeLayer && routeLayer.setStyle) {
                    routeLayer.setStyle({className:'leaflet-polyline-gradient'});
                }
            });
        }
        
        // Update route info with animation - support both old and new formats
        const distance = routeData.distance_km || routeData.distance;
        
        // Handle duration - new endpoint returns seconds, old returns formatted string
        let duration;
        if (routeData.duration_seconds) {
            // New format: use seconds directly
            duration = routeData.duration_seconds;
        } else if (typeof routeData.duration === 'number') {
            // Old format: duration is in seconds
            duration = routeData.duration;
        } else {
            // Fallback: try to parse or use formatted string
            duration = routeData.duration || routeData.durationText || 0;
        }
        
        console.log('Route Info Debug:', {
            distance: distance,
            duration: duration,
            duration_type: typeof duration,
            routeData: routeData
        });
        displayRouteInfo(distance, duration);
        
        // Fit map to show the entire route
        if (routeLayer) {
            if (routeLayer.getBounds) {
                // Single polyline
                map.fitBounds(routeLayer.getBounds(), {padding: [50, 50]});
            } else if (routeLayer.getLayers) {
                // Layer group (traffic segments)
                const group = new L.featureGroup(routeLayer.getLayers());
                map.fitBounds(group.getBounds(), {padding: [50, 50]});
            }
        }
        
        // Show success toast
        showToast('Η διαδρομή υπολογίστηκε επιτυχώς!', 'success');
        
        // Αποθηκεύουμε τα steps για μελλοντική χρήση αν χρειαστεί
        if (routeData.steps) {
            window.routeSteps = routeData.steps;
            // Έλεγχος αν υπάρχει το στοιχείο routeInstructions
            const instructionsElement = document.getElementById('routeInstructions');
            if (instructionsElement) {
                const stepsHtml = routeData.steps.map(step => `<li>${step.instruction}</li>`).join('');
                instructionsElement.innerHTML = `<ol>${stepsHtml}</ol>`;
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Σφάλμα: ' + error.message, 'error');
    })
    .finally(() => {
        // Reset button state
        submitButton.disabled = false;
        document.getElementById('submitBtnText').innerHTML = originalBtnText;
    });
}

function displayRouteInfo(distance, duration) {
    const hours   = Math.floor(duration / 3600);
    const minutes = Math.floor((duration % 3600) / 60);
    const timeStr = hours > 0
        ? `${hours} ώρ${hours > 1 ? '' : ''} ${minutes} λεπ`
        : `${minutes} λεπτά`;

    const routeInfoDiv = document.getElementById('routeInfo');
    if (!routeInfoDiv) return;

    routeInfoDiv.innerHTML = `
        <div class="ri-row">
            <div class="ri-icon"><i class="fas fa-clock"></i></div>
            <div>
                <div class="ri-value">${timeStr}</div>
                <div class="ri-label">Εκτιμώμενος χρόνος</div>
            </div>
        </div>
        <div class="ri-row">
            <div class="ri-icon"><i class="fas fa-road"></i></div>
            <div>
                <div class="ri-value">${distance} χλμ</div>
                <div class="ri-label">Απόσταση</div>
            </div>
        </div>
    `;
    routeInfoDiv.style.display = 'block';
}

function resetMap() {
    // Clear markers
    markers.forEach(m => map.removeLayer(m.marker));
    markers = [];
    
    // Clear route
    if (routeLayer) {
        map.removeLayer(routeLayer);
        routeLayer = null;
    }
    
    // Reset form
    document.getElementById('routeForm').reset();
    document.getElementById('startCoords').value = '';
    document.getElementById('endCoords').value = '';
    
    // Hide route info
    document.getElementById('routeInfo').style.display = 'none';
    
    // Reset map view
    map.setView([38.2, 23.7], 7);
    
    // Show toast
    showToast('Ο χάρτης επαναφέρθηκε', 'info');
}

function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Set icon based on type
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    if (type === 'error') icon = 'exclamation-circle';
    if (type === 'warning') icon = 'exclamation-triangle';
    
    toast.innerHTML = `
        <i class="fas fa-${icon} me-2"></i>
        <span>${message}</span>
    `;
    
    toastContainer.appendChild(toast);
    
    // Remove toast after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            toastContainer.removeChild(toast);
        }, 300);
    }, 3000);
}

function animatePolyline(polyline) {
    let dashArray = '1, 8';
    let dashOffset = 0;
    let interval;
    
    function animate() {
        dashOffset -= 0.5;
        polyline.setStyle({ dashOffset: dashOffset.toString() });
        
        if (Math.abs(dashOffset) > 100) {
            clearInterval(interval);
            polyline.setStyle({ dashArray: null });
        }
    }
    
    interval = setInterval(animate, 20);
}

function animateElements() {
    // Add staggered animation to elements
    const elements = document.querySelectorAll('.fade-in');
    elements.forEach((el, index) => {
        setTimeout(() => {
            el.style.opacity = '1';
            el.style.transform = 'translateY(0)';
        }, 100 * index);
    });
}

// --- Debounce Helper ---
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// --- Custom Polyline with Gradient & Animated Markers ---
let routePolyline = null;
function drawRoutePolyline(coords) {
    if (routePolyline) map.removeLayer(routePolyline);
    // Use leaflet polyline with custom SVG gradient
    routePolyline = L.polyline(coords, {
        color: 'url(#route-gradient)',
        weight: 7,
        opacity: 0.93,
        className: 'leaflet-polyline-gradient',
        lineCap: 'round',
        lineJoin: 'round'
    }).addTo(map);
    // Tooltip with distance
    routePolyline.bindTooltip(
        document.getElementById('distance').textContent + ' χλμ',
        {permanent: false, direction: 'top', className: 'route-tooltip'}
    );
    // Highlight on info hover
    document.querySelector('.route-details').addEventListener('mouseenter',()=>{
        routePolyline.setStyle({className:'leaflet-polyline-gradient leaflet-polyline-highlight'});
    });
    document.querySelector('.route-details').addEventListener('mouseleave',()=>{
        routePolyline.setStyle({className:'leaflet-polyline-gradient'});
    });
}
// --- Custom Markers (Google Maps style) ---
function updateMarker(latlng, type) {
    markers = markers.filter(m => {
        if (m.type === type) { map.removeLayer(m.marker); return false; }
        return true;
    });

    let icon;
    if (type === 'start') {
        icon = L.divIcon({
            className: '',
            html: '<div class="gm-dot-start"></div>',
            iconSize: [14, 14],
            iconAnchor: [7, 7]
        });
    } else {
        icon = L.divIcon({
            className: '',
            html: '<div class="gm-pin-end"></div>',
            iconSize: [24, 30],
            iconAnchor: [12, 28]
        });
    }

    const marker = L.marker(latlng, { icon, riseOnHover: true }).addTo(map);
    markers.push({ marker, type });
}
// --- Copy to Clipboard ---
document.addEventListener('click', function(e) {
    if (e.target.closest('#copyStartCoords')) {
        const val = document.getElementById('startCoords').value;
        navigator.clipboard.writeText(val);
        showToast('Αντιγράφηκε η αφετηρία!', 'success');
    } else if (e.target.closest('#copyEndCoords')) {
        const val = document.getElementById('endCoords').value;
        navigator.clipboard.writeText(val);
        showToast('Αντιγράφηκε ο προορισμός!', 'success');
    }
});
// --- Show Route Instructions ---
function showRouteInstructions(steps) {
    const el = document.getElementById('routeInstructions');
    // Έλεγχος αν το στοιχείο υπάρχει
    if (!el) return;
    
    // Έλεγχος για εγκυρα βήματα
    if (!steps || !Array.isArray(steps) || steps.length === 0) { 
        el.innerHTML = ''; 
        return; 
    }
    
    try {
        // Διασφάλιση ότι κάθε βήμα έχει οδηγία
        const safeSteps = steps.filter(s => s && s.instruction);
        el.innerHTML = '<ol>' + safeSteps.map(s => `<li>${s.instruction}</li>`).join('') + '</ol>';
    } catch (error) {
        console.error('Error displaying route instructions:', error);
        el.innerHTML = '';
    }
}
// --- Integrate with calculateRoute ---
if (!window._origCalculateRoute) {
    window._origCalculateRoute = calculateRoute;
    calculateRoute = function() {
        window._origCalculateRoute.apply(this, arguments);
        // After route is drawn, update polyline and instructions
        setTimeout(() => {
            const routeData = window.lastRouteData;
            if (routeData && routeData.geometry && routeData.geometry.length > 1) drawRoutePolyline(routeData.geometry.map(coord => [coord[1], coord[0]]));
            const routeSteps = routeData && routeData.steps;
            showRouteInstructions(routeSteps);
        }, 400);
    };
}

// --- User Location Marker ---
let userLocationMarker = null;

// Μέθοδος εμφάνισης της τοποθεσίας του χρήστη - διατηρείται για μελλοντική χρήση
function showUserLocation() {
    if (!navigator.geolocation) return showToast('Δεν υποστηρίζεται το geolocation.', 'error');
    navigator.geolocation.getCurrentPosition(pos => {
        const latlng = [pos.coords.latitude, pos.coords.longitude];
        if (userLocationMarker) map.removeLayer(userLocationMarker);
        userLocationMarker = L.marker(latlng, {
            icon: L.divIcon({className: 'user-location-marker'}),
            zIndexOffset: 1000
        }).addTo(map);
        map.setView(latlng, 15, {animate: true});
    }, () => showToast('Αποτυχία εύρεσης τοποθεσίας.', 'error'));
}

// --- Λειτουργίες διαμοιρασμού και εξαγωγής ---
// Κώδικας αφαιρέθηκε αφού τα αντίστοιχα στοιχεία έχουν αφαιρεθεί από το HTML
// Διατηρούμε τη δυνατότητα αποθήκευσης της διαδρομής στο window.lastRouteData
// για χρήση από μελλοντικές λειτουργίες αν χρειαστεί

// --- Clear Route Button ---
const resetMapBtn = document.getElementById('resetMapBtn');
if (resetMapBtn) {
    resetMapBtn.addEventListener('click', function() {
        if (routePolyline) map.removeLayer(routePolyline);
        markers.forEach(m => map.removeLayer(m.marker));
        markers = [];
        document.getElementById('routeInfo').style.display = 'none';
        // Αφαιρούμε την αναφορά στο routeInstructions που δεν υπάρχει πλέον
        const instructionsEl = document.getElementById('routeInstructions');
        if (instructionsEl) instructionsEl.innerHTML = '';
        if (userLocationMarker) map.removeLayer(userLocationMarker);
        showToast('Ο χάρτης καθαρίστηκε.', 'success');
    });
}

// --- Animate Route Drawing ---
function animateRoute(coords) {
    if (routePolyline) map.removeLayer(routePolyline);
    let i = 1;
    routePolyline = L.polyline([coords[0]], {
        color: 'url(#route-gradient)',
        weight: 7,
        opacity: 0.93,
        className: 'leaflet-polyline-gradient',
        lineCap: 'round',
        lineJoin: 'round'
    }).addTo(map);
    const interval = setInterval(() => {
        if (i >= coords.length) return clearInterval(interval);
        routePolyline.addLatLng(coords[i++]);
    }, 35);
}

// Traffic Visualization Functions
function drawTrafficColoredRoute(trafficSegments) {
    // Clear existing route
    if (routeLayer) {
        map.removeLayer(routeLayer);
    }
    
    // Create layer group for all segments
    routeLayer = L.layerGroup().addTo(map);
    
    trafficSegments.forEach((segment, index) => {
        if (segment.coordinates && segment.coordinates.length >= 2) {
            const segmentCoords = segment.coordinates.map(coord => [coord[1], coord[0]]);
            
            const segmentPolyline = L.polyline(segmentCoords, {
                color: segment.color,
                weight: 10,  // Increased weight for better coverage
                opacity: 0.95,
                lineCap: 'round',
                lineJoin: 'round'
            });
            
            // Add tooltip with traffic info
            segmentPolyline.bindTooltip(
                `<strong>Κίνηση:</strong> ${getTrafficLevelText(segment.traffic_level)}<br>
                 <strong>Καθυστέρηση:</strong> ${(segment.delay_factor * 100 - 100).toFixed(0)}%`,
                {
                    sticky: true,
                    className: 'traffic-tooltip'
                }
            );
            
            routeLayer.addLayer(segmentPolyline);
        }
    });
    
    // Fit map to route bounds
    if (routeLayer.getLayers().length > 0) {
        const group = new L.featureGroup(routeLayer.getLayers());
        map.fitBounds(group.getBounds(), {padding: [20, 20]});
    }
    
    // Update route info if available
    if (window.lastRouteData && window.lastRouteData.route) {
        const routeData = window.lastRouteData.route;
        const distance = routeData.distance_km || routeData.distance;
        
        // Handle duration properly
        let duration;
        if (routeData.duration_seconds) {
            duration = routeData.duration_seconds;
        } else if (typeof routeData.duration === 'number') {
            duration = routeData.duration;
        } else {
            duration = 0;
        }
        
        displayRouteInfo(distance, duration);
    }
}

function addTrafficLegend(trafficLegend) {
    // Remove existing legend control
    if (window.trafficLegendControl) {
        map.removeControl(window.trafficLegendControl);
        window.trafficLegendControl = null;
    }
    
    // Create legend HTML
    const legendHtml = `
        <div class="traffic-legend">
            <h4>🚦 Κατάσταση Κίνησης</h4>
            ${Object.entries(trafficLegend).map(([level, info]) => `
                <div class="legend-item">
                    <span class="legend-color" style="background-color: ${info.color}"></span>
                    <span class="legend-text">${info.description}</span>
                </div>
            `).join('')}
        </div>
    `;
    
    // Add legend to map
    const legendControl = L.control({position: 'bottomright'});
    legendControl.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'legend-control');
        div.innerHTML = legendHtml;
        
        // Prevent map events on legend
        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.disableScrollPropagation(div);
        
        return div;
    };
    legendControl.addTo(map);
    
    // Store reference for removal
    window.trafficLegendControl = legendControl;
    
    console.log('Traffic legend added successfully');
}

function getTrafficLevelText(level) {
    const levelTexts = {
        'free_flow': 'Ελεύθερη κίνηση',
        'light': 'Ελαφριά κίνηση',
        'moderate': 'Μέτρια κίνηση',
        'heavy': 'Βαριά κίνηση',
        'unknown': 'Άγνωστη κατάσταση'
    };
    return levelTexts[level] || 'Άγνωστη κατάσταση';
}

// Reset Everything Function
function resetEverything() {
    console.log('🔄 Resetting everything...');
    
    // 1. Clear all input fields
    document.getElementById('startLocation').value = '';
    document.getElementById('endLocation').value = '';
    document.getElementById('startCoords').value = '';
    document.getElementById('endCoords').value = '';
    
    // 2. Clear all markers
    markers.forEach(marker => {
        if (marker && map.hasLayer(marker)) {
            map.removeLayer(marker);
        }
    });
    markers = [];
    
    // 3. Clear route layer
    if (routeLayer) {
        if (routeLayer.getLayers) {
            // Layer group (traffic segments)
            routeLayer.clearLayers();
        }
        map.removeLayer(routeLayer);
        routeLayer = null;
    }
    
    // 4. Clear traffic legend
    if (window.trafficLegendControl) {
        map.removeControl(window.trafficLegendControl);
        window.trafficLegendControl = null;
    }
    
    // 5. Hide route info
    const routeInfoDiv = document.getElementById('routeInfo');
    if (routeInfoDiv) {
        routeInfoDiv.style.display = 'none';
        routeInfoDiv.innerHTML = '';
    }
    
    // 6. Reset map view to Greece
    map.setView([38.2, 23.7], 7);
    
    // 7. Clear global variables
    window.lastRouteData = null;
    window.routeSteps = null;
    
    // 8. Reset form button state
    const submitButton = document.getElementById('routeForm').querySelector('button');
    const submitBtnText = document.getElementById('submitBtnText');
    if (submitButton && submitBtnText) {
        submitButton.disabled = false;
        submitBtnText.innerHTML = '<i class="fas fa-search"></i> Εύρεση Διαδρομής';
    }
    
    // 9. Clear any existing toasts/notifications
    const toastContainer = document.querySelector('.toast-container');
    if (toastContainer) {
        toastContainer.innerHTML = '';
    }
    
    // 10. Focus on start location input for new search
    document.getElementById('startLocation').focus();
    
    // Show success message
    showToast('🔄 Όλα επαναφέρθηκαν! Ξεκινήστε νέα αναζήτηση.', 'success');
    
    console.log('✅ Reset completed successfully');
}

// Use animateRoute instead of drawRoutePolyline in calculateRoute integration
if (!window._origCalculateRoute) {
    window._origCalculateRoute = calculateRoute;
    calculateRoute = function() {
        window._origCalculateRoute.apply(this, arguments);
        setTimeout(() => {
            const routeData = window.lastRouteData;
            if (routeData && routeData.route && routeData.route.geometry) {
                animateRoute(routeData.route.geometry);
            }
            const routeSteps = routeData && routeData.steps;
            showRouteInstructions(routeSteps);
        }, 400);
    };
}
