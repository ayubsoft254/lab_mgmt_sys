"""
Report generation utilities for system usage statistics
"""
from django.utils import timezone
from django.db.models import Count, Q, Sum, F, ExpressionWrapper, DurationField
from datetime import datetime, timedelta
from booking.models import (
    Lab, Computer, ComputerBooking, LabSession, 
    ComputerBookingAttendance, SessionAttendance, User
)


class SystemUsageReporter:
    """Generate comprehensive system usage reports"""
    
    def __init__(self, start_date=None, end_date=None):
        self.end_date = end_date or timezone.now().date()
        self.start_date = start_date or (self.end_date - timedelta(days=30))
    
    def get_date_range_display(self):
        """Get formatted date range"""
        return f"{self.start_date.strftime('%B %d, %Y')} - {self.end_date.strftime('%B %d, %Y')}"
    
    def get_lab_statistics(self):
        """Get comprehensive lab usage statistics"""
        labs = Lab.objects.all()
        lab_stats = []
        
        for lab in labs:
            # Get bookings for this lab within date range
            bookings = ComputerBooking.objects.filter(
                computer__lab=lab,
                start_time__date__gte=self.start_date,
                start_time__date__lte=self.end_date,
                is_approved=True,
                is_cancelled=False
            )
            
            # Get lab sessions for this lab within date range
            sessions = LabSession.objects.filter(
                lab=lab,
                start_time__date__gte=self.start_date,
                start_time__date__lte=self.end_date,
                is_approved=True,
                is_cancelled=False
            )
            
            # Calculate total hours
            booking_hours = 0
            for booking in bookings:
                duration = (booking.end_time - booking.start_time).total_seconds() / 3600
                booking_hours += duration
            
            session_hours = 0
            for session in sessions:
                duration = (session.end_time - session.start_time).total_seconds() / 3600
                session_hours += duration
            
            # Get attendance stats for bookings
            booking_attendance = ComputerBookingAttendance.objects.filter(
                booking__computer__lab=lab,
                booking__start_time__date__gte=self.start_date,
                booking__start_time__date__lte=self.end_date
            )
            
            # Get attendance stats for sessions
            session_attendance = SessionAttendance.objects.filter(
                session__lab=lab,
                session__start_time__date__gte=self.start_date,
                session__start_time__date__lte=self.end_date
            )
            
            lab_stats.append({
                'name': lab.name,
                'location': lab.location,
                'capacity': lab.capacity,
                'computers': lab.computers.count(),
                'bookings': bookings.count(),
                'booking_hours': round(booking_hours, 2),
                'sessions': sessions.count(),
                'session_hours': round(session_hours, 2),
                'total_hours': round(booking_hours + session_hours, 2),
                'utilization': self._calculate_utilization(lab, booking_hours, session_hours),
                'booking_attendance': {
                    'total': booking_attendance.count(),
                    'present': booking_attendance.filter(status='present').count(),
                    'late': booking_attendance.filter(status='late').count(),
                    'absent': booking_attendance.filter(status='absent').count(),
                    'excused': booking_attendance.filter(status='excused').count(),
                },
                'session_attendance': {
                    'total': session_attendance.count(),
                    'present': session_attendance.filter(status='present').count(),
                    'late': session_attendance.filter(status='late').count(),
                    'absent': session_attendance.filter(status='absent').count(),
                    'excused': session_attendance.filter(status='excused').count(),
                }
            })
        
        return lab_stats
    
    def _calculate_utilization(self, lab, booking_hours, session_hours):
        """Calculate lab utilization percentage"""
        # Assuming lab operates 8 hours per day
        days = (self.end_date - self.start_date).days + 1
        max_hours = days * 8 * lab.computers.count()
        
        if max_hours == 0:
            return 0
        
        total_usage = booking_hours + session_hours
        utilization = (total_usage / max_hours) * 100
        return min(100, round(utilization, 2))
    
    def get_computer_statistics(self):
        """Get per-computer usage statistics"""
        computers = Computer.objects.all().select_related('lab')
        computer_stats = []
        
        for computer in computers:
            bookings = ComputerBooking.objects.filter(
                computer=computer,
                start_time__date__gte=self.start_date,
                start_time__date__lte=self.end_date,
                is_approved=True,
                is_cancelled=False
            )
            
            hours = 0
            for booking in bookings:
                duration = (booking.end_time - booking.start_time).total_seconds() / 3600
                hours += duration
            
            computer_stats.append({
                'number': computer.computer_number,
                'lab': computer.lab.name,
                'specs': computer.specs,
                'status': computer.status,
                'bookings': bookings.count(),
                'hours': round(hours, 2),
                'active': computer.status == 'available'
            })
        
        return sorted(computer_stats, key=lambda x: x['hours'], reverse=True)
    
    def get_active_computers(self):
        """Get currently active/available computers"""
        active = Computer.objects.filter(status='available').select_related('lab')
        maintenance = Computer.objects.filter(status='maintenance').select_related('lab')
        reserved = Computer.objects.filter(status='reserved').select_related('lab')
        
        return {
            'available': [
                {
                    'number': c.computer_number,
                    'lab': c.lab.name,
                    'specs': c.specs
                } for c in active
            ],
            'maintenance': [
                {
                    'number': c.computer_number,
                    'lab': c.lab.name,
                    'specs': c.specs
                } for c in maintenance
            ],
            'reserved': [
                {
                    'number': c.computer_number,
                    'lab': c.lab.name,
                    'specs': c.specs
                } for c in reserved
            ],
            'summary': {
                'total': Computer.objects.count(),
                'available_count': active.count(),
                'maintenance_count': maintenance.count(),
                'reserved_count': reserved.count(),
                'availability_percentage': round((active.count() / Computer.objects.count() * 100) if Computer.objects.count() > 0 else 0, 2)
            }
        }
    
    def get_student_statistics(self):
        """Get student usage statistics"""
        students = User.objects.filter(is_student=True)
        
        student_stats = []
        for student in students:
            bookings = ComputerBooking.objects.filter(
                student=student,
                start_time__date__gte=self.start_date,
                start_time__date__lte=self.end_date,
                is_approved=True,
                is_cancelled=False
            )
            
            hours = 0
            for booking in bookings:
                duration = (booking.end_time - booking.start_time).total_seconds() / 3600
                hours += duration
            
            attendance = ComputerBookingAttendance.objects.filter(
                booking__student=student,
                booking__start_time__date__gte=self.start_date,
                booking__start_time__date__lte=self.end_date
            )
            
            if bookings.exists() or attendance.exists():
                student_stats.append({
                    'name': student.get_full_name(),
                    'username': student.username,
                    'school': student.get_school_display() if student.school else 'N/A',
                    'bookings': bookings.count(),
                    'hours': round(hours, 2),
                    'attendance_count': attendance.count(),
                    'attendance_rate': round((attendance.filter(status__in=['present', 'late']).count() / attendance.count() * 100) if attendance.exists() else 0, 2)
                })
        
        return sorted(student_stats, key=lambda x: x['bookings'], reverse=True)[:50]  # Top 50 students
    
    def get_summary_statistics(self):
        """Get overall summary statistics"""
        total_bookings = ComputerBooking.objects.filter(
            start_time__date__gte=self.start_date,
            start_time__date__lte=self.end_date,
            is_approved=True,
            is_cancelled=False
        ).count()
        
        total_sessions = LabSession.objects.filter(
            start_time__date__gte=self.start_date,
            start_time__date__lte=self.end_date,
            is_approved=True,
            is_cancelled=False
        ).count()
        
        booking_attendance = ComputerBookingAttendance.objects.filter(
            booking__start_time__date__gte=self.start_date,
            booking__start_time__date__lte=self.end_date
        )
        
        session_attendance = SessionAttendance.objects.filter(
            session__start_time__date__gte=self.start_date,
            session__start_time__date__lte=self.end_date
        )
        
        total_hours = 0
        for booking in ComputerBooking.objects.filter(
            start_time__date__gte=self.start_date,
            start_time__date__lte=self.end_date,
            is_approved=True,
            is_cancelled=False
        ):
            duration = (booking.end_time - booking.start_time).total_seconds() / 3600
            total_hours += duration
        
        for session in LabSession.objects.filter(
            start_time__date__gte=self.start_date,
            start_time__date__lte=self.end_date,
            is_approved=True,
            is_cancelled=False
        ):
            duration = (session.end_time - session.start_time).total_seconds() / 3600
            total_hours += duration
        
        return {
            'report_generated': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
            'date_range': self.get_date_range_display(),
            'total_bookings': total_bookings,
            'total_sessions': total_sessions,
            'total_users': User.objects.filter(is_student=True).count(),
            'total_labs': Lab.objects.count(),
            'total_computers': Computer.objects.count(),
            'total_hours': round(total_hours, 2),
            'booking_attendance': {
                'total': booking_attendance.count(),
                'present': booking_attendance.filter(status='present').count(),
                'late': booking_attendance.filter(status='late').count(),
                'absent': booking_attendance.filter(status='absent').count(),
                'excused': booking_attendance.filter(status='excused').count(),
            },
            'session_attendance': {
                'total': session_attendance.count(),
                'present': session_attendance.filter(status='present').count(),
                'late': session_attendance.filter(status='late').count(),
                'absent': session_attendance.filter(status='absent').count(),
                'excused': session_attendance.filter(status='excused').count(),
            }
        }
    
    def get_full_report_context(self):
        """Get complete report context for template rendering"""
        return {
            'summary': self.get_summary_statistics(),
            'labs': self.get_lab_statistics(),
            'computers': self.get_computer_statistics(),
            'active_computers': self.get_active_computers(),
            'top_students': self.get_student_statistics(),
        }
