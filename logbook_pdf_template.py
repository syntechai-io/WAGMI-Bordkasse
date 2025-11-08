from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas
from datetime import datetime
from typing import List, Dict, Any, Optional
import io

def render_logbook_pdf(
    entries: List[Any],
    vessel: Dict[str, str],
    scope: str,
    outfile: Any,
    meta: Optional[Dict[str, Any]] = None,
    summary: Optional[Dict[str, Any]] = None
) -> None:
    """
    Render official German/European standard logbook PDF export.
    
    Args:
        entries: List of LogbookEntry objects to export
        vessel: Dictionary with vessel info (name, home_port, call_sign, etc.)
        scope: Export scope ("single_entry", "daily", "full_trip")
        outfile: File-like object or path to write PDF
        meta: Optional metadata (creator, title, subject)
        summary: Optional summary statistics (total_nm, total_engine_hours, etc.)
    """
    
    doc = SimpleDocTemplate(
        outfile,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
        title=meta.get('title', 'Logbuch') if meta else 'Logbuch'
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a3a52'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#1a3a52'),
        spaceAfter=6,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.black,
        fontName='Helvetica'
    )
    
    small_style = ParagraphStyle(
        'CustomSmall',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#555555'),
        fontName='Helvetica'
    )
    
    story = []
    
    title_text = "Bordbuch / Ship's Log"
    if scope == "single_entry":
        title_text = "Bordbuch-Eintrag / Logbook Entry"
    elif scope == "daily":
        title_text = "Tageslogbuch / Daily Log"
    
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 8*mm))
    
    vessel_data = [
        ['Schiffsname / Vessel Name:', vessel.get('name', '-')],
        ['Heimathafen / Home Port:', vessel.get('home_port', '-')],
        ['Rufzeichen / Call Sign:', vessel.get('call_sign', '-')],
        ['IMO/MMSI:', vessel.get('imo_mmsi', '-')]
    ]
    
    vessel_table = Table(vessel_data, colWidths=[60*mm, 100*mm])
    vessel_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a3a52')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(vessel_table)
    story.append(Spacer(1, 6*mm))
    
    for idx, entry in enumerate(entries):
        if idx > 0:
            story.append(Spacer(1, 5*mm))
            story.append(Paragraph('─' * 80, small_style))
            story.append(Spacer(1, 3*mm))
        
        entry_date_str = entry.entry_date.strftime('%d.%m.%Y %H:%M') if entry.entry_date else '-'
        
        story.append(Paragraph(f'<b>Eintrag vom / Entry from:</b> {entry_date_str}', heading_style))
        
        basic_data = []
        
        if entry.latitude or entry.longitude:
            lat_str = f"{entry.latitude:.6f}" if entry.latitude else "-"
            lon_str = f"{entry.longitude:.6f}" if entry.longitude else "-"
            basic_data.append(['Position (Lat/Lon):', f'{lat_str} / {lon_str}'])
        
        if entry.departure or entry.destination:
            route_str = f"{entry.departure or '-'} → {entry.destination or '-'}"
            basic_data.append(['Route:', route_str])
        
        if entry.cog_deg is not None or entry.sog_kn is not None:
            nav_str = f"COG: {entry.cog_deg}° " if entry.cog_deg is not None else ""
            nav_str += f"SOG: {entry.sog_kn} kn" if entry.sog_kn is not None else ""
            basic_data.append(['Kurs/Geschw. (Course/Speed):', nav_str.strip()])
        
        if entry.log_kn is not None:
            basic_data.append(['Log (kn):', f'{entry.log_kn} kn'])
        
        if entry.dist_day_nm is not None:
            basic_data.append(['Tagesstrecke (nm):', f'{entry.dist_day_nm} nm'])
        
        if basic_data:
            basic_table = Table(basic_data, colWidths=[60*mm, 100*mm])
            basic_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a3a52')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(basic_table)
            story.append(Spacer(1, 3*mm))
        
        weather_data = []
        
        if entry.wind_direction or entry.wind_strength:
            wind_str = f"{entry.wind_direction or ''} {entry.wind_strength or ''}".strip()
            weather_data.append(['Wind:', wind_str])
        
        if entry.sea_state:
            weather_data.append(['Seegang (Sea State):', entry.sea_state.value if hasattr(entry.sea_state, 'value') else str(entry.sea_state)])
        
        if entry.visibility:
            weather_data.append(['Sicht (Visibility):', entry.visibility])
        
        if entry.temperature is not None:
            weather_data.append(['Temperatur:', f'{entry.temperature}°C'])
        
        if entry.pressure_hpa is not None:
            pressure_str = f"{entry.pressure_hpa} hPa"
            if entry.pressure_trend:
                trend_symbol = {'steigend': '↗', 'fallend': '↘', 'gleichbleibend': '→'}.get(entry.pressure_trend, '')
                pressure_str += f" {trend_symbol}"
            weather_data.append(['Luftdruck (Pressure):', pressure_str])
        
        if entry.weather_source:
            weather_data.append(['Wetterquelle (Source):', entry.weather_source])
        
        if weather_data:
            story.append(Paragraph('<b>Wetter / Weather:</b>', normal_style))
            weather_table = Table(weather_data, colWidths=[60*mm, 100*mm])
            weather_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a3a52')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(weather_table)
            story.append(Spacer(1, 3*mm))
        
        sail_data = []
        
        if entry.sail_plan:
            sail_data.append(['Segelplan (Sail Plan):', entry.sail_plan])
        
        if entry.main_furl_pct is not None:
            sail_data.append(['Großsegel (Mainsail):', f'{entry.main_furl_pct}% ausgerollt'])
        
        if entry.headsail:
            sail_data.append(['Vorsegel (Headsail):', entry.headsail])
        
        if entry.sail_action:
            sail_data.append(['Segelaktion:', entry.sail_action])
        
        if sail_data:
            story.append(Paragraph('<b>Segel / Sails:</b>', normal_style))
            sail_table = Table(sail_data, colWidths=[60*mm, 100*mm])
            sail_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a3a52')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(sail_table)
            story.append(Spacer(1, 3*mm))
        
        engine_data = []
        
        if entry.engine_on is not None:
            engine_status = "AN (ON)" if entry.engine_on else "AUS (OFF)"
            engine_data.append(['Motor Status:', engine_status])
        
        if entry.engine_on_time:
            engine_data.append(['Motor AN um:', entry.engine_on_time.strftime('%d.%m.%Y %H:%M')])
        
        if entry.engine_off_time:
            engine_data.append(['Motor AUS um:', entry.engine_off_time.strftime('%d.%m.%Y %H:%M')])
        
        if entry.eng_hours_total is not None:
            engine_data.append(['Motorstunden gesamt:', f'{entry.eng_hours_total} h'])
        elif entry.engine_hours is not None:
            engine_data.append(['Motorstunden:', f'{entry.engine_hours} h'])
        
        if entry.fuel_level_l is not None:
            engine_data.append(['Kraftstoff (Fuel):', f'{entry.fuel_level_l} L'])
        
        if engine_data:
            story.append(Paragraph('<b>Motor / Engine:</b>', normal_style))
            engine_table = Table(engine_data, colWidths=[60*mm, 100*mm])
            engine_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a3a52')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(engine_table)
            story.append(Spacer(1, 3*mm))
        
        if hasattr(entry, 'crew_on_watch') and entry.crew_on_watch:
            crew_names = [f"{watch.member.code} - {watch.member.name}" for watch in entry.crew_on_watch if watch.member]
            if crew_names:
                story.append(Paragraph(f'<b>Wache (Watch):</b> {", ".join(crew_names)}', normal_style))
                story.append(Spacer(1, 2*mm))
        
        if entry.event_category or entry.event_details:
            story.append(Paragraph('<b>Ereignis / Event:</b>', normal_style))
            event_data = []
            if entry.event_category:
                event_data.append(['Kategorie:', entry.event_category])
            if entry.event_details:
                event_data.append(['Details:', entry.event_details])
            
            event_table = Table(event_data, colWidths=[60*mm, 100*mm])
            event_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a3a52')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(event_table)
            story.append(Spacer(1, 3*mm))
        
        if entry.notes:
            story.append(Paragraph('<b>Notizen / Notes:</b>', normal_style))
            story.append(Paragraph(entry.notes, normal_style))
            story.append(Spacer(1, 2*mm))
        
        if entry.safety_checks_completed:
            story.append(Paragraph('<b>Sicherheitschecks / Safety Checks:</b>', normal_style))
            story.append(Paragraph(entry.safety_checks_completed, normal_style))
            story.append(Spacer(1, 2*mm))
        
        if hasattr(entry, 'parent_id') and entry.parent_id:
            story.append(Paragraph(f'<i>Nachtrag zu Eintrag #{entry.parent_id}</i>', small_style))
            if entry.change_note:
                story.append(Paragraph(f'<i>Änderungsnotiz: {entry.change_note}</i>', small_style))
            story.append(Spacer(1, 2*mm))
    
    if summary:
        story.append(Spacer(1, 8*mm))
        story.append(Paragraph('<b>Zusammenfassung / Summary:</b>', heading_style))
        
        summary_data = []
        if summary.get('total_nm'):
            summary_data.append(['Gesamtstrecke (Total Distance):', f"{summary['total_nm']} nm"])
        if summary.get('total_engine_hours'):
            summary_data.append(['Motorstunden gesamt:', f"{summary['total_engine_hours']} h"])
        if summary.get('entry_count'):
            summary_data.append(['Anzahl Einträge (Entries):', str(summary['entry_count'])])
        
        if summary_data:
            summary_table = Table(summary_data, colWidths=[60*mm, 100*mm])
            summary_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a3a52')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(summary_table)
    
    story.append(Spacer(1, 10*mm))
    
    footer_text = f"Erstellt am / Generated: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    story.append(Paragraph(footer_text, small_style))
    
    story.append(Spacer(1, 5*mm))
    
    signature_data = [
        ['_' * 40, '_' * 40],
        ['Unterschrift Skipper / Signature', 'Ort, Datum / Place, Date']
    ]
    signature_table = Table(signature_data, colWidths=[80*mm, 80*mm])
    signature_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 1), (-1, 1), 6),
    ]))
    story.append(signature_table)
    
    doc.build(story)
