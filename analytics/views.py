from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, View
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from .models import SystemEvent


class SystemEventListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """View for listing system events with filtering capabilities"""
    model = SystemEvent
    template_name = 'system_events/list.html'
    context_object_name = 'events'
    permission_required = 'system_events.view_systemevent'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = SystemEvent.objects.with_related()
        
        # Filter by event type if specified
        event_type = self.request.GET.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
            
        # Filter by severity if specified
        severity = self.request.GET.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
            
        # Filter by resolved status if specified
        resolved = self.request.GET.get('resolved')
        if resolved == 'true':
            queryset = queryset.filter(resolved=True)
        elif resolved == 'false':
            queryset = queryset.filter(resolved=False)
            
        # Filter by user if specified
        user_id = self.request.GET.get('user_id')
        if user_id:
            queryset = queryset.filter(user__id=user_id)
            
        # Filter by date range if specified
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(timestamp__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__lte=date_to)
            
        # Search if query is provided
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(user__username__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(details__icontains=search_query) |
                Q(event_type__icontains=search_query)
            )
            
        return queryset.order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event_types'] = SystemEvent.EventTypes.choices
        context['severity_levels'] = SystemEvent.SeverityLevels.choices
        return context


class SystemEventDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detailed view for a single system event"""
    model = SystemEvent
    template_name = 'system_events/detail.html'
    context_object_name = 'event'
    permission_required = 'system_events.view_systemevent'
    
    def get_queryset(self):
        return SystemEvent.objects.with_related()


class DashboardEventsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """View for displaying recent events on dashboard"""
    model = SystemEvent
    template_name = 'system_events/dashboard.html'
    context_object_name = 'events'
    permission_required = 'system_events.view_systemevent'
    
    def get_queryset(self):
        days = int(self.request.GET.get('days', 7))
        return SystemEvent.objects.for_dashboard(days=days)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['days'] = int(self.request.GET.get('days', 7))
        return context


class UserEventsView(LoginRequiredMixin, ListView):
    """View for displaying events related to the current user"""
    model = SystemEvent
    template_name = 'system_events/user_events.html'
    context_object_name = 'events'
    paginate_by = 15
    
    def get_queryset(self):
        days = int(self.request.GET.get('days', 30))
        return SystemEvent.objects.get_events_for_user(
            user=self.request.user,
            days=days
        ).order_by('-timestamp')


class SecurityEventsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """View for displaying security-related events"""
    model = SystemEvent
    template_name = 'system_events/security_events.html'
    context_object_name = 'events'
    permission_required = 'system_events.view_systemevent'
    paginate_by = 25
    
    def get_queryset(self):
        days = int(self.request.GET.get('days', 30))
        return SystemEvent.objects.get_security_events(days=days)


class CriticalEventsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """View for displaying critical severity events"""
    model = SystemEvent
    template_name = 'system_events/critical_events.html'
    context_object_name = 'events'
    permission_required = 'system_events.view_systemevent'
    
    def get_queryset(self):
        return SystemEvent.objects.critical_events().unresolved().order_by('-timestamp')


class UnresolvedEventsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """View for displaying unresolved events"""
    model = SystemEvent
    template_name = 'system_events/unresolved_events.html'
    context_object_name = 'events'
    permission_required = 'system_events.view_systemevent'
    paginate_by = 25
    
    def get_queryset(self):
        return SystemEvent.objects.unresolved().order_by('-severity', '-timestamp')


class ResolveEventView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """View for marking an event as resolved"""
    permission_required = 'system_events.change_systemevent'
    
    def post(self, request, pk):
        event = get_object_or_404(SystemEvent, pk=pk)
        event.mark_as_resolved(request.user)
        messages.success(request, f"Event #{event.id} has been marked as resolved.")
        
        # Return to the appropriate page
        redirect_to = request.POST.get('redirect_to', 'system_events:list')
        return redirect(redirect_to)


class EventsJsonView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """JSON API endpoint for events data"""
    permission_required = 'system_events.view_systemevent'
    
    def get(self, request):
        limit = int(request.GET.get('limit', 10))
        event_type = request.GET.get('event_type')
        severity = request.GET.get('severity')
        
        queryset = SystemEvent.objects.all()
        
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if severity:
            queryset = queryset.filter(severity=severity)
            
        events = queryset.order_by('-timestamp')[:limit]
        
        data = {
            'events': [
                {
                    'id': event.id,
                    'event_type': event.get_event_type_display(),
                    'timestamp': event.timestamp.isoformat(),
                    'user': event.user.username if event.user else None,
                    'severity': event.get_severity_display(),
                    'resolved': event.resolved,
                    'details': event.details,
                    'icon': event.get_event_icon(),
                }
                for event in events
            ]
        }
        
        return JsonResponse(data)