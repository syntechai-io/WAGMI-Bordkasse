/**
 * Logbook Quick Entry System
 * Manages maneuver type selection
 */

class LogbookQuickEntry {
    constructor() {
        this.currentType = 'full';
        this.init();
    }

    init() {
        // Set up maneuver type buttons
        const buttons = document.querySelectorAll('.maneuver-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const type = btn.getAttribute('data-type');
                this.setManeuverType(type);
            });
        });

        // Initialize from saved value
        const savedType = document.getElementById('maneuver_type_input')?.value;
        if (savedType) {
            this.setManeuverType(savedType);
        } else {
            this.setManeuverType('full');
        }
    }

    setManeuverType(type) {
        this.currentType = type;
        
        // Update hidden input
        const input = document.getElementById('maneuver_type_input');
        if (input) {
            input.value = type;
        }

        // Update button styles
        document.querySelectorAll('.maneuver-btn').forEach(btn => {
            if (btn.getAttribute('data-type') === type) {
                btn.style.borderColor = 'var(--sea-foam)';
                btn.style.background = 'linear-gradient(135deg, rgba(46, 204, 113, 0.1) 0%, rgba(52, 152, 219, 0.1) 100%)';
                btn.style.borderWidth = '3px';
            } else {
                btn.style.borderColor = 'var(--sky-blue)';
                btn.style.background = 'white';
                btn.style.borderWidth = '2px';
            }
        });

        // For now, always show all fields (full entry mode)
        // Future: implement conditional field visibility based on maneuver type
        this.updateFieldVisibility(type);
    }

    updateFieldVisibility(type) {
        // Simple implementation: show all fields for "full", hide optional sections for quick entry modes
        // This can be enhanced later with explicit data-maneuver attributes on sections
        
        if (type === 'full') {
            // Show everything
            this.showAllFields();
        } else {
            // For quick entry modes, show all for now
            // TODO: Add data-maneuver attributes to form sections and implement selective visibility
            this.showAllFields();
        }
    }

    showAllFields() {
        // Ensure all sections are visible
        const sections = document.querySelectorAll('[data-maneuver]');
        sections.forEach(section => {
            section.style.display = '';
            section.style.opacity = '1';
        });
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    new LogbookQuickEntry();
});
