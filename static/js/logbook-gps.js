/**
 * Logbook GPS Tracking Module
 * Provides continuous foreground GPS tracking for sailing logbook entries
 * iOS Restriction: Background tracking not supported, foreground only
 */

class LogbookGPSTracker {
    constructor() {
        this.watchId = null;
        this.isTracking = false;
        this.lastPosition = null;
        this.trackingStartTime = null;
        this.positionHistory = [];
        this.maxHistorySize = 10; // Keep last 10 positions for averaging
        this.wakeLock = null;
    }

    /**
     * Start continuous GPS tracking
     */
    start() {
        if (this.isTracking) {
            console.log('GPS tracking already active');
            return;
        }

        if (!('geolocation' in navigator)) {
            alert('❌ Geolocation nicht unterstützt!\n\nIhr Browser unterstützt keine GPS-Funktionen.');
            return;
        }

        const options = {
            enableHighAccuracy: true,
            timeout: 30000,
            maximumAge: 5000  // Accept positions up to 5 seconds old
        };

        this.watchId = navigator.geolocation.watchPosition(
            (position) => this.onPositionUpdate(position),
            (error) => this.onPositionError(error),
            options
        );

        this.isTracking = true;
        this._requestWakeLock();
        this.trackingStartTime = new Date();
        this.positionHistory = [];
        
        console.log('GPS tracking started');
        this.dispatchEvent('tracking-started');
    }

    /**
     * Stop GPS tracking
     */
    stop() {
        if (!this.isTracking) {
            return;
        }

        if (this.watchId !== null) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }

        this.isTracking = false;
        this._releaseWakeLock();
        this.trackingStartTime = null;
        
        console.log('GPS tracking stopped');
        this.dispatchEvent('tracking-stopped');
    }

    /**
     * Handle position update from GPS
     */
    onPositionUpdate(position) {
        this.lastPosition = position;
        
        // Add to history
        this.positionHistory.push({
            timestamp: position.timestamp,
            coords: {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                speed: position.coords.speed,
                heading: position.coords.heading,
                accuracy: position.coords.accuracy
            }
        });

        // Keep history size limited
        if (this.positionHistory.length > this.maxHistorySize) {
            this.positionHistory.shift();
        }

        // Auto-fill form fields
        this.updateFormFields();

        // Dispatch custom event for UI updates
        this.dispatchEvent('position-update', { position });
    }

    /**
     * Handle GPS errors
     */
    onPositionError(error) {
        let errorMessage = '';
        
        switch(error.code) {
            case error.PERMISSION_DENIED:
                errorMessage = 'GPS-Zugriff verweigert';
                this.stop();
                break;
            case error.POSITION_UNAVAILABLE:
                errorMessage = 'GPS-Signal nicht verfügbar';
                break;
            case error.TIMEOUT:
                errorMessage = 'GPS-Timeout';
                break;
            default:
                errorMessage = 'GPS-Fehler';
        }

        console.warn(`GPS Error: ${errorMessage}`, error);
        this.dispatchEvent('position-error', { error, errorMessage });
    }

    /**
     * Update form fields with current GPS data
     */
    updateFormFields() {
        if (!this.lastPosition) return;

        const coords = this.lastPosition.coords;

        // Update latitude/longitude
        const latInput = document.querySelector('input[name="latitude"]');
        const lonInput = document.querySelector('input[name="longitude"]');
        
        if (latInput) latInput.value = coords.latitude.toFixed(6);
        if (lonInput) lonInput.value = coords.longitude.toFixed(6);

        // Update SOG (Speed Over Ground) - convert m/s to knots
        if (coords.speed !== null && coords.speed >= 0) {
            const sogInput = document.querySelector('input[name="sog_kn"]');
            if (sogInput) {
                const speedKnots = (coords.speed * 1.94384).toFixed(1);
                sogInput.value = speedKnots;
            }
        }

        // Update COG (Course Over Ground) - heading in degrees
        if (coords.heading !== null && coords.heading >= 0) {
            const cogInput = document.querySelector('input[name="cog_deg"]');
            if (cogInput) {
                const heading = Math.round(coords.heading);
                cogInput.value = heading;
            }
        }
    }

    /**
     * Get averaged position from history (reduces GPS jitter)
     * iOS often returns null heading/speed when stationary, so those values
     * are skipped from the average instead of being treated as zero.
     */
    getAveragedPosition() {
        if (this.positionHistory.length === 0) return null;

        let latSum = 0, lonSum = 0, speedSum = 0, speedCount = 0;
        let headingSum = 0, headingCount = 0;

        this.positionHistory.forEach(pos => {
            latSum += pos.coords.latitude;
            lonSum += pos.coords.longitude;
            if (pos.coords.speed !== null && pos.coords.speed >= 0) {
                speedSum += pos.coords.speed;
                speedCount++;
            }
            if (pos.coords.heading !== null && pos.coords.heading >= 0) {
                headingSum += pos.coords.heading;
                headingCount++;
            }
        });

        const count = this.positionHistory.length;
        return {
            latitude:  latSum / count,
            longitude: lonSum / count,
            speed:     speedCount > 0 ? speedSum / speedCount : null,
            heading:   headingCount > 0 ? headingSum / headingCount : null,
        };
    }

    /**
     * Get current tracking status
     */
    getStatus() {
        return {
            isTracking: this.isTracking,
            lastPosition: this.lastPosition,
            trackingDuration: this.trackingStartTime 
                ? new Date() - this.trackingStartTime 
                : 0,
            positionCount: this.positionHistory.length
        };
    }

    /**
     * Dispatch custom events
     */
    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(`gps-${eventName}`, { 
            detail,
            bubbles: true 
        });
        document.dispatchEvent(event);
    }

    /**
     * Request a screen wake lock so iOS does not put the screen to sleep
     * (and kill GPS) while tracking is active. Silently no-ops on browsers
     * without the Wake Lock API or when the OS denies the request.
     */
    async _requestWakeLock() {
        if ('wakeLock' in navigator) {
            try {
                this.wakeLock = await navigator.wakeLock.request('screen');
                this.wakeLock.addEventListener('release', () => {
                    this.wakeLock = null;
                });
            } catch (e) {
                // Wake lock not granted — acceptable, tracking continues
            }
        }
    }

    /**
     * Release any held wake lock.
     */
    _releaseWakeLock() {
        if (this.wakeLock) {
            this.wakeLock.release().catch(() => {});
            this.wakeLock = null;
        }
    }
}

// Create global instance
window.logbookGPSTracker = new LogbookGPSTracker();
