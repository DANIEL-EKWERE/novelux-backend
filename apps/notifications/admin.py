from django.contrib import admin

from apps.users.models import FCMDevice
from .models import Notification
# from users.models import FCMDevice  
# DeviceToken




from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django import forms
from .models import PushNotificationLog
# from users.models import FCMDevice
from .services import (notify_all, notify_user, notify_by_genre)
 
 
class SendNotificationForm(forms.Form):
    title     = forms.CharField(max_length=200)
    body      = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}))
    image_url = forms.URLField(required=False, label='Image URL (optional)')
    audience  = forms.ChoiceField(choices=[
        ('all',      'All users'),
        ('android',  'Android only'),
        ('ios',      'iOS only'),
        ('genre',    'By genre preference'),
    ])
    genre_slug = forms.CharField(required=False,
                     help_text='Required only when audience = By genre')
    extra_data = forms.CharField(required=False,
                     widget=forms.Textarea(attrs={'rows': 2}),
                     help_text='JSON payload e.g. {"screen": "contest"}')
 
 
@admin.register(PushNotificationLog)
class PushNotificationLogAdmin(admin.ModelAdmin):
    list_display  = ['title', 'audience', 'status', 'sent_count',
                     'failed_count', 'created_by', 'created_at']
    list_filter   = ['status', 'audience', 'created_at']
    readonly_fields = ['status', 'sent_count', 'failed_count',
                       'sent_at', 'created_at']
    search_fields = ['title', 'body']
 
    # Custom changelist action — "Send new notification" button
    change_list_template = 'notifications/push_changelist.html'
 
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('send/', self.admin_site.admin_view(self.send_view),
                 name='notifications_send'),
        ]
        return custom + urls
 
    def send_view(self, request):
        from django.shortcuts import render
        import json
        from django.contrib import messages
 
        if request.method == 'POST':
            form = SendNotificationForm(request.POST)
            if form.is_valid():
                cd        = form.cleaned_data
                title     = cd['title']
                body      = cd['body']
                audience  = cd['audience']
                image_url = cd.get('image_url', '')
                genre     = cd.get('genre_slug', '')
                try:
                    data = json.loads(cd['extra_data']) if cd['extra_data'] else {}
                except Exception:
                    data = {}
 
                log = PushNotificationLog.objects.create(
                    title=title, body=body,
                    data=data, image_url=image_url,
                    audience=audience, genre_slug=genre,
                    created_by=request.user, status='pending')
 
                result = {'success': 0, 'failed': 0}
                try:
                    if audience in ('all', 'android', 'ios'):
                        from apps.users.models import FCMDevice
                        qs = FCMDevice.objects.filter(is_active=True)
                        if audience == 'android':
                            qs = qs.filter(platform='Android')
                        elif audience == 'ios':
                            qs = qs.filter(platform='iOS')
                        from .fcm import send_to_tokens
                        CHUNK = 500
                        tokens = list(qs.values_list('token', flat=True))
                        for i in range(0, len(tokens), CHUNK):
                            r = send_to_tokens(tokens[i:i+CHUNK],
                                               title, body, data, image_url)
                            result['success'] += r['success']
                            result['failed']  += r['failed']
                    elif audience == 'genre' and genre:
                        notify_by_genre(genre, title, body, data)
 
                    from django.utils import timezone
                    log.status       = 'sent'
                    log.sent_count   = result['success']
                    log.failed_count = result['failed']
                    log.sent_at      = timezone.now()
                    log.save()
                    messages.success(request,
                        f'Sent to {result["success"]} devices '
                        f'({result["failed"]} failed)')
                except Exception as e:
                    log.status = 'failed'; log.save()
                    messages.error(request, f'Failed: {e}')
 
                return HttpResponseRedirect('../')
        else:
            form = SendNotificationForm()
 
        return render(request, 'notifications/send_push.html',
                      {'form': form, 'title': 'Send Push Notification'})
 
 
# @admin.register(DeviceToken)
# class DeviceTokenAdmin(admin.ModelAdmin):
#     list_display  = ['user', 'platform', 'device_model',
#                      'is_active', 'updated_at']
#     list_filter   = ['platform', 'is_active']
#     search_fields = ['user__username', 'token', 'device_model']
#     readonly_fields = ['token', 'created_at', 'updated_at']


#TODO: working on somthing here

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ['recipient', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter   = ['notification_type', 'is_read']
    search_fields = ['recipient__username', 'title']
    readonly_fields = ['recipient', 'notification_type', 'title', 'message', 'data', 'created_at']


# @admin.register(DeviceToken)
# class DeviceTokenAdmin(admin.ModelAdmin):
#     list_display  = ['user', 'platform', 'is_active', 'created_at']
#     list_filter   = ['platform', 'is_active']
#     search_fields = ['user__username']
