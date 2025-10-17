"""
Views for generating system usage reports
"""
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os
from .utils import SystemUsageReporter


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and (user.is_admin or user.is_super_admin)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def reports_dashboard(request):
    """Display reports dashboard with available report options"""
    context = {
        'page_title': 'System Reports',
        'reports': [
            {
                'title': 'System Usage Report',
                'description': 'Comprehensive system usage including lab statistics, computer usage, and attendance data',
                'url': 'system_usage',
                'icon': 'chart-line',
                'color': 'primary'
            },
            {
                'title': 'Lab Utilization Report',
                'description': 'Detailed lab usage, capacity analysis, and utilization trends',
                'url': 'lab_utilization',
                'icon': 'bar-chart',
                'color': 'info'
            },
            {
                'title': 'Computer Inventory Report',
                'description': 'Computer status, active machines, maintenance schedule, and usage metrics',
                'url': 'computer_inventory',
                'icon': 'desktop',
                'color': 'success'
            },
            {
                'title': 'Attendance Report',
                'description': 'Attendance statistics, student participation, and engagement metrics',
                'url': 'attendance',
                'icon': 'clipboard-check',
                'color': 'warning'
            }
        ]
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def system_usage_report(request):
    """Generate system usage report (HTML view)"""
    # Get date range from query parameters
    days = int(request.GET.get('days', 30))
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Generate report
    reporter = SystemUsageReporter(start_date, end_date)
    context = reporter.get_full_report_context()
    context['days'] = days
    context['start_date'] = start_date
    context['end_date'] = end_date
    
    # Check if PDF export is requested
    if request.GET.get('format') == 'pdf':
        return generate_pdf_report(reporter, 'system_usage')
    
    return render(request, 'reports/system_usage.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def lab_utilization_report(request):
    """Generate lab utilization report (HTML view)"""
    days = int(request.GET.get('days', 30))
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    reporter = SystemUsageReporter(start_date, end_date)
    labs = reporter.get_lab_statistics()
    
    context = {
        'page_title': 'Lab Utilization Report',
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
        'labs': labs,
        'summary': reporter.get_summary_statistics(),
    }
    
    if request.GET.get('format') == 'pdf':
        return generate_pdf_report(reporter, 'lab_utilization')
    
    return render(request, 'reports/lab_utilization.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def computer_inventory_report(request):
    """Generate computer inventory report (HTML view)"""
    reporter = SystemUsageReporter()
    computers = reporter.get_computer_statistics()
    active = reporter.get_active_computers()
    
    context = {
        'page_title': 'Computer Inventory Report',
        'computers': computers,
        'active_computers': active,
        'summary': reporter.get_summary_statistics(),
    }
    
    if request.GET.get('format') == 'pdf':
        return generate_pdf_report(reporter, 'computer_inventory')
    
    return render(request, 'reports/computer_inventory.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def attendance_report(request):
    """Generate attendance report (HTML view)"""
    days = int(request.GET.get('days', 30))
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    reporter = SystemUsageReporter(start_date, end_date)
    
    context = {
        'page_title': 'Attendance Report',
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
        'summary': reporter.get_summary_statistics(),
        'top_students': reporter.get_student_statistics(),
    }
    
    if request.GET.get('format') == 'pdf':
        return generate_pdf_report(reporter, 'attendance')
    
    return render(request, 'reports/attendance.html', context)


def generate_pdf_report(reporter, report_type):
    """Generate PDF report using ReportLab"""
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Define custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c6e49'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c6e49'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    # Header
    story.append(Paragraph("Lab Management System", title_style))
    story.append(Paragraph(f"System Usage Report", styles['Heading2']))
    story.append(Spacer(1, 0.2*inch))
    
    summary = reporter.get_summary_statistics()
    
    # Summary section
    story.append(Paragraph("Report Summary", heading_style))
    
    summary_data = [
        ['Metric', 'Value'],
        ['Report Generated', summary['report_generated']],
        ['Date Range', summary['date_range']],
        ['Total Bookings', str(summary['total_bookings'])],
        ['Total Lab Sessions', str(summary['total_sessions'])],
        ['Total Hours Logged', f"{summary['total_hours']} hours"],
        ['Active Students', str(summary['total_users'])],
        ['Total Labs', str(summary['total_labs'])],
        ['Total Computers', str(summary['total_computers'])],
    ]
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c6e49')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Attendance Statistics
    if report_type in ['system_usage', 'attendance']:
        story.append(Paragraph("Attendance Statistics", heading_style))
        
        booking_att = summary['booking_attendance']
        session_att = summary['session_attendance']
        
        attendance_data = [
            ['Category', 'Total', 'Present', 'Late', 'Absent', 'Excused'],
            ['Computer Bookings', str(booking_att['total']), str(booking_att['present']), 
             str(booking_att['late']), str(booking_att['absent']), str(booking_att['excused'])],
            ['Lab Sessions', str(session_att['total']), str(session_att['present']), 
             str(session_att['late']), str(session_att['absent']), str(session_att['excused'])],
        ]
        
        att_table = Table(attendance_data)
        att_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c6e49')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
        ]))
        
        story.append(att_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Lab Statistics
    if report_type in ['system_usage', 'lab_utilization']:
        story.append(PageBreak())
        story.append(Paragraph("Lab Utilization", heading_style))
        
        labs = reporter.get_lab_statistics()
        
        for lab in labs[:5]:  # Limit to first 5 labs per page
            lab_data = [
                ['Lab Information', 'Value'],
                ['Lab Name', lab['name']],
                ['Location', lab['location']],
                ['Capacity', f"{lab['computers']} computers"],
                ['Total Bookings', str(lab['bookings'])],
                ['Total Sessions', str(lab['sessions'])],
                ['Usage Hours', f"{lab['total_hours']} hours"],
                ['Utilization', f"{lab['utilization']}%"],
            ]
            
            lab_table = Table(lab_data, colWidths=[2.5*inch, 2.5*inch])
            lab_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e4c33')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')])
            ]))
            
            story.append(lab_table)
            story.append(Spacer(1, 0.15*inch))
    
    # Computer Statistics
    if report_type in ['system_usage', 'computer_inventory']:
        story.append(PageBreak())
        story.append(Paragraph("Computer Usage Statistics", heading_style))
        
        computers = reporter.get_computer_statistics()[:20]  # Top 20 computers
        
        computer_data = [['Computer #', 'Lab', 'Status', 'Bookings', 'Hours Used']]
        for comp in computers:
            computer_data.append([
                str(comp['number']),
                comp['lab'],
                comp['status'].title(),
                str(comp['bookings']),
                f"{comp['hours']}"
            ])
        
        comp_table = Table(computer_data)
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c6e49')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
        ]))
        
        story.append(comp_table)
    
    # Build PDF
    doc.build(story)
    
    # Return as file response
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="system-usage-report-{datetime.now().strftime("%Y-%m-%d")}.pdf"'
    
    return response
