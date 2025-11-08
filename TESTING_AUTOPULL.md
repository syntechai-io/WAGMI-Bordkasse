# Logbook Auto-Pull Features - Manual Testing Guide

## Overview
This document provides manual testing procedures for all logbook auto-pull features including GPS data extraction, continuous tracking, and motor hours auto-calculation.

## Prerequisites
- Access to device with GPS capabilities (smartphone recommended)
- Active trip selected in Crew Wallet application
- Location permissions granted for the website

---

## Test Suite 1: GPS Single Position Pull

### Test 1.1: Basic GPS Position Retrieval
**Steps:**
1. Navigate to "Neuer Logbuch-Eintrag" (New logbook entry)
2. Click "📍 GPS-Position abrufen" button
3. Grant location permission if prompted
4. Wait for GPS signal

**Expected Results:**
- Button shows "⏳ GPS-Position wird abgerufen..."
- After successful read: Button shows "✅ Position abgerufen!"
- Latitude field auto-filled with value like `54.083300`
- Longitude field auto-filled with value like `13.437800`
- Button returns to "📍 GPS-Position abrufen" after 2 seconds

**Pass/Fail Criteria:**
- ✅ Latitude and longitude fields contain valid decimal coordinates
- ✅ Values match device's current location (verify with Maps app)

### Test 1.2: GPS Speed (SOG) Extraction
**Prerequisites:** Device must be in motion (walk, drive, or sail)

**Steps:**
1. Start moving (walk at steady pace or drive slowly)
2. Click "📍 GPS-Position abrufen" while moving
3. Wait for GPS fix

**Expected Results:**
- SOG field auto-filled with speed in knots
- Speed value is reasonable (walking = ~1-2 knots, driving slow = 5-10 knots)

**Formula Verification:**
- 1 m/s = 1.94384 knots
- Walking speed ~1.5 m/s should show ~2.9 knots
- Driving 10 km/h (~2.78 m/s) should show ~5.4 knots

**Pass/Fail Criteria:**
- ✅ SOG field populated with numeric value ≥ 0
- ✅ Value is reasonable for current movement speed
- ✅ Stationary device shows 0.0 or very low value (<0.5 knots)

### Test 1.3: GPS Heading (COG) Extraction
**Prerequisites:** Device must be in motion with clear direction

**Steps:**
1. Start moving in a known direction (e.g., walking North)
2. Click "📍 GPS-Position abrufen" while moving in straight line
3. Wait for GPS fix

**Expected Results:**
- COG field auto-filled with heading in degrees (0-359)
- Heading roughly matches direction of travel:
  - North = 0° or 360°
  - East = 90°
  - South = 180°
  - West = 270°

**Pass/Fail Criteria:**
- ✅ COG field populated with integer value 0-359
- ✅ Direction is reasonable (± 45° of known direction)

### Test 1.4: Null Speed/Heading Handling
**Steps:**
1. Test GPS indoors or in poor signal conditions
2. Click "📍 GPS-Position abrufen"
3. Allow GPS to acquire position

**Expected Results:**
- Latitude/longitude should populate (low accuracy is OK)
- SOG and COG fields may remain empty if GPS doesn't provide speed/heading
- No JavaScript errors in browser console

**Pass/Fail Criteria:**
- ✅ Application doesn't crash when speed/heading unavailable
- ✅ Lat/lon still populate successfully
- ✅ Empty SOG/COG fields don't break form submission

---

## Test Suite 2: Continuous GPS Tracking

### Test 2.1: Start Tracking
**Steps:**
1. Navigate to logbook entry form
2. Click "🎯 GPS-Tracking starten"
3. Grant location permission if prompted

**Expected Results:**
- Button changes to "⏸️ GPS-Tracking stoppen" (red background)
- Tracking banner appears below buttons
- Banner shows "🛰️" with pulsing animation
- Status text shows "Warte auf GPS-Signal..."

**Pass/Fail Criteria:**
- ✅ Tracking banner is visible
- ✅ Button indicates active tracking
- ✅ No errors in console

### Test 2.2: Active Tracking Updates
**Steps:**
1. Start GPS tracking (as above)
2. Wait for first position fix
3. Move to different location
4. Observe updates

**Expected Results:**
- After first fix, banner shows:
  - Current position coordinates
  - "Genauigkeit: XX m" (accuracy in meters)
  - "Letztes Update: HH:MM:SS" (last update time)
- Position fields update automatically every 5 seconds
- SOG and COG update as you move
- Accuracy improves over time (typically < 20m after 30 seconds)

**Pass/Fail Criteria:**
- ✅ Position updates occur at least once per 10 seconds
- ✅ Coordinates change when device moves
- ✅ Last update time refreshes
- ✅ Accuracy value is reasonable (< 50m for outdoor, < 100m indoor)

### Test 2.3: Stop Tracking
**Steps:**
1. With tracking active, click "⏸️ GPS-Tracking stoppen"

**Expected Results:**
- Button changes back to "🎯 GPS-Tracking starten" (blue background)
- Tracking banner disappears
- Form fields retain last captured values

**Pass/Fail Criteria:**
- ✅ Tracking stops (no more updates)
- ✅ UI returns to initial state
- ✅ Last captured data remains in form

### Test 2.4: Tracking Error Handling
**Steps:**
1. Start tracking in good GPS conditions
2. Move indoors to area with no GPS signal
3. Observe banner status

**Expected Results:**
- Banner shows error message like "GPS-Signal nicht verfügbar"
- Tracking continues attempting to acquire signal
- Last good position remains in fields

**Pass/Fail Criteria:**
- ✅ Error message displayed clearly
- ✅ Application doesn't crash
- ✅ Tracking can resume when signal returns

---

## Test Suite 3: Motor Hours Auto-Calculation

### Test 3.1: Basic Duration Calculation
**Steps:**
1. Navigate to "Motor & Antrieb" section
2. Click "▶️ Motor AN" button (auto-sets current time)
3. Wait 5 seconds (or manually adjust time to 10 minutes later)
4. Click "⏸️ Motor AUS" button

**Expected Results:**
- Engine On Time: auto-filled with timestamp
- Engine Off Time: auto-filled with timestamp
- Console logs duration calculation
- If eng_hours_total field has value, duration is added to it

**Formula Verification:**
- Example: On=10:00, Off=11:30
- Duration = 1.5 hours
- If starting total = 123.5h, new total = 125.0h

**Pass/Fail Criteria:**
- ✅ Motor AN button sets engine_on_time to current time
- ✅ Motor AUS button sets engine_off_time to current time
- ✅ Duration calculation is accurate (± 0.1 hour)

### Test 3.2: Manual Time Adjustment
**Steps:**
1. Manually enter Engine On Time: `2025-11-08T10:00`
2. Manually enter Engine Off Time: `2025-11-08T13:45`
3. Tab out of the Off Time field (triggers change event)

**Expected Results:**
- Duration auto-calculates: 3.75 hours (3 hours 45 minutes)
- If eng_hours_total = 100.0, new value = 103.8

**Pass/Fail Criteria:**
- ✅ Manual time entry triggers calculation
- ✅ Duration is correct: 3 hours 45 min = 3.8 hours (rounded to 1 decimal)

### Test 3.3: Empty Total Hours (First Entry Scenario)
**Steps:**
1. Leave "Motorstunden Gesamt" field empty
2. Set engine on/off times (duration = 2.5 hours)

**Expected Results:**
- Duration is calculated but NOT auto-filled to total field
- User must manually enter starting hours (e.g., if first trip of year)
- Console shows calculation but doesn't modify empty field

**Pass/Fail Criteria:**
- ✅ Empty eng_hours_total field remains empty
- ✅ User can manually enter starting value
- ✅ After manual entry, future calculations will add to it

### Test 3.4: Invalid Time Order Rejection
**Steps:**
1. Set Engine On Time: `10:00`
2. Set Engine Off Time: `09:00` (before on time)
3. Observe behavior

**Expected Results:**
- No calculation occurs (invalid)
- Console shows validation message
- eng_hours_total not modified

**Pass/Fail Criteria:**
- ✅ Invalid time order doesn't cause crash
- ✅ No incorrect calculation

---

## Test Suite 4: Offline Storage with Auto-Pulled Data

### Test 4.1: Offline Entry with GPS Data
**Steps:**
1. Enable airplane mode on device
2. Navigate to new logbook entry form
3. Use GPS tracking to capture position (fails - no signal)
4. Manually enter lat/lon, SOG, COG
5. Set motor times
6. Fill watch leader, sails, etc.
7. Submit form

**Expected Results:**
- Form shows "✅ Offline gespeichert!" message
- Entry stored in IndexedDB
- All fields including auto-pulled data are saved
- Entry syncs when connection restored

**Pass/Fail Criteria:**
- ✅ Offline submission succeeds
- ✅ GPS fields, motor hours, watch leader all saved
- ✅ Data syncs correctly when online

---

## Test Suite 5: Integration & End-to-End

### Test 5.1: Complete Sailing Entry
**Scenario:** Create realistic logbook entry while sailing

**Steps:**
1. Start GPS tracking at beginning of watch
2. Let tracking run for 5-10 minutes (captures position changes)
3. Set motor times when engine used
4. Configure sails (mainsail furling %, genua state)
5. Select watch leader from crew dropdown
6. Add weather data, notes
7. Submit entry

**Expected Results:**
- All auto-pulled fields populated:
  - GPS: lat, lon, SOG, COG
  - Motor: on/off times, duration calculated
  - Crew: watch leader selected
  - Sails: mainsail 50%, genua gesetzt
- Entry saves successfully
- Detail view shows all captured data

**Pass/Fail Criteria:**
- ✅ Entry creation successful
- ✅ All auto-pulled data visible in detail view
- ✅ PDF export includes GPS and motor data
- ✅ Append-only history preserved (no edit allowed)

### Test 5.2: PDF Export Verification
**Steps:**
1. Create entry with auto-pulled GPS and motor data (as above)
2. Navigate to entry detail view
3. Click "PDF Export" button
4. Download and open PDF

**Expected Results:**
- PDF contains:
  - Position coordinates
  - SOG and COG values
  - Engine on/off times
  - Motor hours total
  - Watch leader name
  - All sail configuration
- German/European maritime logbook format
- Signature fields present

**Pass/Fail Criteria:**
- ✅ PDF downloads successfully
- ✅ All auto-pulled fields visible in PDF
- ✅ Values match entry detail view
- ✅ Format meets official standards

---

## Performance Benchmarks

### GPS Tracking Performance
- **First position fix:** < 10 seconds (outdoor)
- **Update frequency:** Every 5-10 seconds
- **Position accuracy:** < 20m (optimal), < 50m (typical)
- **Battery impact:** Moderate (foreground GPS tracking)

### Motor Calculation Performance
- **Calculation time:** < 1ms (instant)
- **Form responsiveness:** No lag

### Offline Storage Performance
- **Save time:** < 100ms
- **Sync time:** < 2 seconds per entry (when online)

---

## Known Limitations

### GPS Tracking
1. **iOS Background Restriction:** GPS tracking only works while page is active (foreground)
2. **Signal Required:** Indoor tracking may fail or have poor accuracy
3. **Speed/Heading Availability:** Some devices don't provide speed/heading when stationary

### Motor Hours
1. **Manual Starting Value:** User must know and enter starting engine hours for first trip of year
2. **No Cross-Entry Context:** Each entry calculates independently

### Browser Compatibility
- **Chrome/Safari:** Full support
- **Firefox:** Full support
- **Older browsers:** May lack geolocation API

---

## Bug Reporting Template

If you encounter issues, report using this format:

```
**Feature:** GPS Tracking / Motor Hours / Etc.
**Browser:** Chrome 120 / Safari 17 / etc.
**Device:** iPhone 15 / Samsung S24 / etc.
**Location:** Indoor / Outdoor / Moving / Stationary
**Steps to Reproduce:**
1. 
2. 
3. 

**Expected Behavior:**

**Actual Behavior:**

**Console Errors:** (from browser dev tools)

**Screenshots:** (if applicable)
```

---

## Test Sign-Off

Tester: ___________________________
Date: ___________________________
Version: ___________________________

Test Results:
- [ ] All GPS single position tests passed
- [ ] All continuous tracking tests passed
- [ ] All motor hours tests passed
- [ ] All offline storage tests passed
- [ ] End-to-end integration tests passed
- [ ] PDF export verified

Notes:
_____________________________________________
_____________________________________________
_____________________________________________
