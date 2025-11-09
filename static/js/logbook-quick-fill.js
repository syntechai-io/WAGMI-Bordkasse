document.addEventListener('DOMContentLoaded', () => {
    const quickFillBtn = document.getElementById('quick-fill-button');
    if (!quickFillBtn) return;

    quickFillBtn.addEventListener('click', async () => {
        const btnText = document.getElementById('quick-fill-text');
        const btnSpinner = document.getElementById('quick-fill-spinner');
        
        btnText.classList.add('hidden');
        btnSpinner.classList.remove('hidden');
        quickFillBtn.disabled = true;

        const results = {
            dateTime: false,
            gps: false,
            gpsDetails: null,
            weather: false
        };

        try {
            // Always fill date/time - this never fails
            fillCurrentDateTime();
            results.dateTime = true;
            
            // Try GPS with error handling
            try {
                const gpsResult = await fillGPSData();
                results.gps = true;
                results.gpsDetails = gpsResult;
            } catch (gpsError) {
                console.warn('GPS failed:', gpsError);
                // Continue anyway - we can still fill weather manually
            }
            
            // Try weather if we have GPS coords
            const lat = document.querySelector('input[name="latitude"]').value;
            const lon = document.querySelector('input[name="longitude"]').value;
            
            if (lat && lon) {
                try {
                    await fillWeatherData();
                    results.weather = true;
                } catch (weatherError) {
                    console.warn('Weather fetch failed:', weatherError);
                }
            }
            
            btnText.classList.remove('hidden');
            btnSpinner.classList.add('hidden');
            quickFillBtn.disabled = false;
            
            // Show appropriate success message based on what was actually populated
            if (results.gps && results.weather) {
                if (results.gpsDetails && results.gpsDetails.hasSogCog) {
                    showNotification('✅ Alle Daten erfolgreich abgerufen!', 'success');
                } else {
                    showNotification('✅ Uhrzeit, GPS Position und Wetter abgerufen. SOG/COG nicht verfügbar.', 'info');
                }
            } else if (results.gps) {
                if (results.gpsDetails && results.gpsDetails.hasSogCog) {
                    showNotification('✅ Uhrzeit und GPS erfolgreich. Wetter konnte nicht abgerufen werden.', 'info');
                } else {
                    showNotification('✅ Uhrzeit und GPS Position erfolgreich. SOG/COG und Wetter nicht verfügbar.', 'info');
                }
            } else if (results.weather) {
                showNotification('✅ Uhrzeit und Wetter erfolgreich. GPS konnte nicht abgerufen werden.', 'info');
            } else {
                showNotification('✅ Uhrzeit gesetzt. GPS und Wetter konnten nicht abgerufen werden. Bitte GPS-Berechtigung erteilen.', 'info');
            }
        } catch (error) {
            console.error('Quick Fill error:', error);
            btnText.classList.remove('hidden');
            btnSpinner.classList.add('hidden');
            quickFillBtn.disabled = false;
            showNotification('⚠️ Fehler beim Abrufen: ' + error.message, 'error');
        }
    });
});

function fillCurrentDateTime() {
    return new Promise((resolve) => {
        const now = new Date();
        
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const dateStr = `${year}-${month}-${day}`;
        
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const timeStr = `${hours}:${minutes}`;
        
        const dateInput = document.querySelector('input[name="entry_date"]');
        const timeInput = document.querySelector('input[name="entry_time"]');
        
        if (dateInput) dateInput.value = dateStr;
        if (timeInput) timeInput.value = timeStr;
        
        resolve();
    });
}

function fillGPSData() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('GPS nicht verfügbar'));
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                const speed = position.coords.speed;
                const heading = position.coords.heading;

                let fieldsSet = 0;

                // Always have lat/lon
                document.querySelector('input[name="latitude"]').value = lat.toFixed(6);
                document.querySelector('input[name="longitude"]').value = lon.toFixed(6);
                fieldsSet += 2;

                // Only count SOG/COG if actually populated
                if (speed !== null && speed !== undefined && speed >= 0) {
                    const speedKnots = (speed * 1.94384).toFixed(1);
                    const sogInput = document.querySelector('input[name="sog_kn"]');
                    if (sogInput) {
                        sogInput.value = speedKnots;
                        fieldsSet++;
                    }
                }

                if (heading !== null && heading !== undefined && heading >= 0) {
                    const cogInput = document.querySelector('input[name="cog_deg"]');
                    if (cogInput) {
                        cogInput.value = Math.round(heading);
                        fieldsSet++;
                    }
                }

                // Resolve with info about what was set
                resolve({ fieldsSet, hasSogCog: fieldsSet >= 4 });
            },
            (error) => {
                console.error('GPS error:', error);
                reject(new Error('GPS-Position konnte nicht abgerufen werden'));
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    });
}

async function fillWeatherData() {
    const lat = document.querySelector('input[name="latitude"]').value;
    const lon = document.querySelector('input[name="longitude"]').value;

    if (!lat || !lon) {
        throw new Error('GPS-Position erforderlich für Wetterdaten');
    }

    try {
        const response = await fetch(`/logbook/weather?lat=${lat}&lon=${lon}`);
        if (!response.ok) {
            throw new Error('Wetter-API Fehler');
        }

        const data = await response.json();

        if (data.temperature) {
            const tempInput = document.querySelector('input[name="temperature"]');
            if (tempInput) tempInput.value = data.temperature;
        }

        if (data.wind_direction) {
            setHybridFieldValue('wind_direction', data.wind_direction);
        }

        if (data.wind_strength) {
            setHybridFieldValue('wind_strength', data.wind_strength);
        }

        if (data.pressure) {
            const pressureInput = document.querySelector('input[name="pressure_hpa"]');
            if (pressureInput) pressureInput.value = data.pressure;
        }

        const weatherSourceInput = document.querySelector('input[name="weather_source"]');
        if (weatherSourceInput) {
            weatherSourceInput.value = 'Open-Meteo API (Quick Fill)';
        }

    } catch (error) {
        console.error('Weather fetch error:', error);
        throw error;
    }
}

function setHybridFieldValue(fieldName, value) {
    // Use existing hybrid controls if available (from logbook form hybrid system)
    if (window.hybridControls && window.hybridControls[fieldName]) {
        const control = window.hybridControls[fieldName];
        const activeControl = control.getActiveControl();
        if (activeControl) {
            activeControl.value = value;
            // Sync both controls to keep them in sync
            if (typeof control.syncAll === 'function') {
                control.syncAll();
            }
            return;
        }
    }
    
    // Fallback: try to find the active control manually
    const manualInput = document.querySelector(`input[name="${fieldName}"]`);
    const selectInput = document.querySelector(`select[name="${fieldName}"]`);
    
    // Prefer the control that has the name attribute (means it's active)
    if (manualInput && manualInput.name === fieldName) {
        manualInput.value = value;
        // Also update the select if it exists and has the same value option
        if (selectInput) {
            const option = Array.from(selectInput.options).find(opt => opt.value === value);
            if (option) {
                selectInput.value = value;
            }
        }
    } else if (selectInput && selectInput.name === fieldName) {
        selectInput.value = value;
        // Also update the manual input if it exists
        if (manualInput) {
            manualInput.value = value;
        }
    } else if (manualInput) {
        manualInput.value = value;
    } else if (selectInput) {
        selectInput.value = value;
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-20 right-4 z-50 px-6 py-4 rounded-lg shadow-xl transition-all duration-300 transform translate-x-full`;
    
    if (type === 'success') {
        notification.style.background = 'linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)';
    } else if (type === 'error') {
        notification.style.background = 'linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)';
    } else {
        notification.style.background = 'linear-gradient(135deg, #3498db 0%, #2980b9 100%)';
    }
    
    notification.style.color = 'white';
    notification.innerHTML = `<div class="font-bold">${message}</div>`;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 10);
    
    setTimeout(() => {
        notification.style.transform = 'translateX(150%)';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}
