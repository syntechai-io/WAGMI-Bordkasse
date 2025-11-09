from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas
from datetime import datetime
from typing import List, Dict, Any, Optional
import io
import os

def render_logbook_pdf(
    entries: List[Any],
    vessel: Dict[str, str],
    scope: str,
    outfile: Any,
    meta: Optional[Dict[str, Any]] = None,
    summary: Optional[Dict[str, Any]] = None,
    entry_id: Optional[int] = None,
    trip_name: Optional[str] = None,
    crew_list: Optional[List[Dict[str, str]]] = None,
    skipper: Optional[Dict[str, str]] = None
) -> None:
    """
    Render official German/European standard logbook PDF export in traditional grid format.
    
    Args:
        entries: List of LogbookEntry objects to export
        vessel: Dictionary with vessel info (name, home_port, call_sign, etc.)
        scope: Export scope ("single_entry", "daily", "full_trip")
        outfile: File-like object or path to write PDF
        meta: Optional metadata (creator, title, subject)
        summary: Optional summary statistics (total_nm, total_engine_hours, etc.)
        entry_id: Optional entry ID for navigation link (single entry exports)
        trip_name: Optional trip name for display
        crew_list: Optional list of crew members (code and name)
        skipper: Optional skipper info (code and name)
    """
    
    # Use landscape orientation for wider table
    doc = SimpleDocTemplate(
        outfile,
        pagesize=landscape(A4),
        rightMargin=10*mm,
        leftMargin=10*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
        title=meta.get('title', 'Bordbuch') if meta else 'Bordbuch'
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#1a3a52'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        leading=8
    )
    
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=7,
        textColor=colors.black,
        fontName='Helvetica',
        leading=8,
        alignment=TA_LEFT
    )
    
    small_style = ParagraphStyle(
        'SmallStyle',
        parent=styles['Normal'],
        fontSize=6,
        textColor=colors.HexColor('#555555'),
        fontName='Helvetica'
    )
    
    story = []
    
    # Header with vessel info
    title_text = "BORDBUCH / SHIP'S LOG"
    if scope == "daily":
        if entries and entries[0].entry_date:
            date_str = entries[0].entry_date.strftime('%d.%m.%Y')
            title_text = f"TAGESLOGBUCH / DAILY LOG - {date_str}"
    
    story.append(Paragraph(title_text, title_style))
    
    # Vessel info in compact format
    vessel_info = f"<b>Schiff/Vessel:</b> {vessel.get('name', '-')}  |  " \
                 f"<b>Heimathafen/Home Port:</b> {vessel.get('home_port', '-')}  |  " \
                 f"<b>Rufzeichen/Call Sign:</b> {vessel.get('call_sign', '-')}"
    
    vessel_para = Paragraph(vessel_info, ParagraphStyle(
        'VesselInfo',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#1a3a52'),
        alignment=TA_CENTER
    ))
    story.append(vessel_para)
    
    # Skipper and crew roster
    if skipper or crew_list:
        crew_parts = []
        if skipper and skipper.get('name') and skipper.get('name') != '-':
            crew_parts.append(f"<b>Skipper:</b> {skipper.get('name')} ({skipper.get('code', '-')})")
        
        if crew_list:
            crew_names = [f"{c.get('name')} ({c.get('code')})" for c in crew_list]
            if crew_names:
                crew_parts.append(f"<b>Crew:</b> {', '.join(crew_names)}")
        
        if crew_parts:
            crew_info_text = "  |  ".join(crew_parts)
            crew_para = Paragraph(crew_info_text, ParagraphStyle(
                'CrewInfo',
                parent=styles['Normal'],
                fontSize=7,
                textColor=colors.HexColor('#555555'),
                alignment=TA_CENTER
            ))
            story.append(crew_para)
    
    story.append(Spacer(1, 4*mm))
    
    # Build logbook table with all entries
    # Column headers (German/English)
    table_data = [[
        Paragraph('<b>Zeit<br/>Time</b>', header_style),
        Paragraph('<b>Position<br/>Lat/Lon</b>', header_style),
        Paragraph('<b>Kurs<br/>COG</b>', header_style),
        Paragraph('<b>Fahrt<br/>SOG</b>', header_style),
        Paragraph('<b>Log<br/>(nm)</b>', header_style),
        Paragraph('<b>Wind<br/>Richt/Stärke</b>', header_style),
        Paragraph('<b>Wetter<br/>Temp/Druck</b>', header_style),
        Paragraph('<b>Motor<br/>Engine</b>', header_style),
        Paragraph('<b>Segel<br/>Sails</b>', header_style),
        Paragraph('<b>Wache<br/>Watch</b>', header_style),
        Paragraph('<b>Bemerkungen<br/>Notes</b>', header_style),
    ]]
    
    # Add each entry as a row
    for entry in entries:
        # Time
        time_str = entry.entry_date.strftime('%H:%M') if entry.entry_date else '-'
        
        # Position
        pos_str = '-'
        if entry.latitude is not None and entry.longitude is not None:
            lat = f"{abs(entry.latitude):.2f}°{'N' if entry.latitude >= 0 else 'S'}"
            lon = f"{abs(entry.longitude):.2f}°{'E' if entry.longitude >= 0 else 'W'}"
            pos_str = f"{lat}<br/>{lon}"
        
        # COG (Course Over Ground)
        cog_str = f"{entry.cog_deg}°" if entry.cog_deg is not None else '-'
        
        # SOG (Speed Over Ground)
        sog_str = f"{entry.sog_kn} kn" if entry.sog_kn is not None else '-'
        
        # Log (distance)
        log_str = f"{entry.dist_day_nm}" if entry.dist_day_nm is not None else '-'
        
        # Wind
        wind_str = '-'
        if entry.wind_direction or entry.wind_strength:
            wind_parts = []
            if entry.wind_direction:
                wind_parts.append(entry.wind_direction)
            if entry.wind_strength:
                wind_parts.append(entry.wind_strength)
            wind_str = '<br/>'.join(wind_parts)
        
        # Weather (temperature and pressure)
        weather_parts = []
        if entry.temperature is not None:
            weather_parts.append(f"{entry.temperature}°C")
        if entry.pressure_hpa is not None:
            pressure_str = f"{entry.pressure_hpa}hPa"
            if entry.pressure_trend:
                trend_sym = {'steigend': '↗', 'fallend': '↘', 'gleichbleibend': '→'}.get(entry.pressure_trend, '')
                pressure_str += trend_sym
            weather_parts.append(pressure_str)
        weather_str = '<br/>'.join(weather_parts) if weather_parts else '-'
        
        # Engine
        engine_parts = []
        if entry.engine_on is not None:
            engine_parts.append("AN" if entry.engine_on else "AUS")
        if entry.eng_hours_total is not None:
            engine_parts.append(f"{entry.eng_hours_total}h")
        elif entry.engine_hours is not None:
            engine_parts.append(f"{entry.engine_hours}h")
        engine_str = '<br/>'.join(engine_parts) if engine_parts else '-'
        
        # Sails
        sail_parts = []
        if entry.main_furl_pct is not None:
            sail_parts.append(f"Groß {entry.main_furl_pct}%")
        if entry.headsail:
            sail_parts.append(f"{entry.headsail}")
        if entry.sail_action:
            sail_parts.append(entry.sail_action)
        sail_str = '<br/>'.join(sail_parts) if sail_parts else '-'
        
        # Watch (crew)
        watch_str = '-'
        if hasattr(entry, 'crew_on_watch') and entry.crew_on_watch:
            crew_codes = [watch.member.code for watch in entry.crew_on_watch if watch.member]
            watch_str = ', '.join(crew_codes) if crew_codes else '-'
        
        # Notes (compact)
        notes_parts = []
        if entry.departure or entry.destination:
            route = f"{entry.departure or ''} → {entry.destination or ''}".strip(' →')
            notes_parts.append(route)
        if entry.notes:
            # Truncate long notes
            note_text = entry.notes if len(entry.notes) <= 100 else entry.notes[:97] + '...'
            notes_parts.append(note_text)
        if entry.event_details:
            event_text = entry.event_details if len(entry.event_details) <= 50 else entry.event_details[:47] + '...'
            notes_parts.append(f"⚠ {event_text}")
        notes_str = '<br/>'.join(notes_parts) if notes_parts else '-'
        
        # Add row to table
        table_data.append([
            Paragraph(time_str, cell_style),
            Paragraph(pos_str, cell_style),
            Paragraph(cog_str, cell_style),
            Paragraph(sog_str, cell_style),
            Paragraph(log_str, cell_style),
            Paragraph(wind_str, cell_style),
            Paragraph(weather_str, cell_style),
            Paragraph(engine_str, cell_style),
            Paragraph(sail_str, cell_style),
            Paragraph(watch_str, cell_style),
            Paragraph(notes_str, cell_style),
        ])
    
    # Create the table with column widths optimized for landscape A4
    col_widths = [
        18*mm,  # Time
        22*mm,  # Position
        15*mm,  # COG
        15*mm,  # SOG
        12*mm,  # Log
        20*mm,  # Wind
        22*mm,  # Weather
        18*mm,  # Engine
        22*mm,  # Sails
        18*mm,  # Watch
        55*mm,  # Notes (largest)
    ]
    
    logbook_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Table styling to match traditional logbook
    table_style = TableStyle([
        # Header row styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3a52')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # Data rows styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        
        # Grid lines (traditional logbook has visible grid)
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        
        # Cell padding
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        
        # Alternating row colors for readability
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ])
    
    logbook_table.setStyle(table_style)
    story.append(logbook_table)
    
    # Summary section (if provided)
    if summary:
        story.append(Spacer(1, 5*mm))
        summary_parts = []
        if summary.get('total_nm'):
            summary_parts.append(f"Gesamtstrecke/Total Distance: {summary['total_nm']} nm")
        if summary.get('total_engine_hours'):
            summary_parts.append(f"Motorstunden/Engine Hours: {summary['total_engine_hours']} h")
        if summary.get('entry_count'):
            summary_parts.append(f"Einträge/Entries: {summary['entry_count']}")
        
        if summary_parts:
            summary_text = "  |  ".join(summary_parts)
            summary_para = Paragraph(f"<b>ZUSAMMENFASSUNG / SUMMARY:</b> {summary_text}", 
                                    ParagraphStyle('Summary', parent=styles['Normal'], fontSize=8))
            story.append(summary_para)
    
    # Footer with timestamp and navigation
    story.append(Spacer(1, 5*mm))
    
    footer_parts = [f"Erstellt/Generated: {datetime.now().strftime('%d.%m.%Y %H:%M')}"]
    if trip_name:
        footer_parts.append(f"Reise/Trip: {trip_name}")
    
    # Navigation link
    replit_domain = os.environ.get('REPLIT_DOMAINS', '')
    if replit_domain:
        base_url = f"https://{replit_domain}"
        logbook_url = f"{base_url}/logbook"
        footer_parts.append(f'📱 Zurück zum Logbuch/Back to Logbook')
    
    footer_text = "  |  ".join(footer_parts)
    footer_para = Paragraph(footer_text, small_style)
    story.append(footer_para)
    
    # Signature line
    story.append(Spacer(1, 8*mm))
    sig_data = [
        ['_' * 60, '_' * 40],
        ['Unterschrift Skipper / Signature', 'Ort, Datum / Place, Date']
    ]
    sig_table = Table(sig_data, colWidths=[100*mm, 80*mm])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, 1), 4),
    ]))
    story.append(sig_table)
    
    doc.build(story)
