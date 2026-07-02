from django.contrib import admin
from django.utils import timezone
from .models import (
    EditorAssignment, AuthorEditorLink,
    #   ChapterReview,
    EditorialNote, ContentFlag, PolicyDecision, EditorialPolicy,
    SystemNotice, PromotionSlotConfig, StoryPromotion,
    SEPromotionRequest, ExploreTabPin,
)


@admin.register(EditorAssignment)
class EditorAssignmentAdmin(admin.ModelAdmin):
    list_display  = ['editor', 'supervisor', 'assigned_at']
    list_filter   = ['editor__role', 'supervisor__role']
    search_fields = ['editor__username', 'supervisor__username']
    autocomplete_fields = ['editor', 'supervisor']


@admin.register(AuthorEditorLink)
class AuthorEditorLinkAdmin(admin.ModelAdmin):
    list_display  = ['author', 'assigned_se', 'assigned_at']
    search_fields = ['author__username', 'assigned_se__username']
    autocomplete_fields = ['author', 'assigned_se']

    def get_supervising_se(self, obj):
        se = obj.get_supervising_se()
        return se.username if se else '—'
    get_supervising_se.short_description = 'Supervising SE'


class EditorialNoteInline(admin.TabularInline):
    model      = EditorialNote
    extra      = 0
    fields     = ['author', 'note_type', 'content', 'paragraph', 'is_resolved']
    readonly_fields = ['author', 'created_at']


class ContentFlagInline(admin.TabularInline):
    model   = ContentFlag
    extra   = 0
    fields  = ['flagged_by', 'flag_type', 'description', 'resolved']
    readonly_fields = ['flagged_by', 'created_at']


# @admin.register(ChapterReview)
# class ChapterReviewAdmin(admin.ModelAdmin):
#     list_display   = ['chapter', 'author', 'assigned_ae', 'assigned_se',
#                       'status', 'priority', 'submitted_at', 'turnaround_hours']
#     list_filter    = ['status', 'priority', 'submitted_at']
#     search_fields  = ['chapter__title', 'author__username', 'assigned_ae__username']
#     readonly_fields = ['submitted_at', 'updated_at', 'resolved_at']
#     inlines        = [EditorialNoteInline, ContentFlagInline]
#     autocomplete_fields = ['chapter', 'author', 'assigned_ae', 'assigned_se', 'assigned_ce']

#     fieldsets = (
#         ('Chapter', {
#             'fields': ('chapter', 'author'),
#         }),
#         ('Assignment', {
#             'fields': ('assigned_ae', 'assigned_se', 'assigned_ce'),
#         }),
#         ('Status', {
#             'fields': ('status', 'priority', 'submitted_at', 'updated_at', 'resolved_at'),
#         }),
#         ('Scores', {
#             'fields': ('pacing_score', 'dialogue_score', 'consistency_score'),
#             'classes': ('collapse',),
#         }),
#     )


@admin.register(EditorialNote)
class EditorialNoteAdmin(admin.ModelAdmin):
    list_display  = ['chapter', 'written_by', 'note_type', 'is_resolved', 'created_at']
    list_filter   = ['note_type', 'is_resolved']
    search_fields = ['content', 'written_by__username']


@admin.register(ContentFlag)
class ContentFlagAdmin(admin.ModelAdmin):
    list_display  = ['chapter', 'flagged_by', 'flag_type', 'resolved', 'created_at']
    list_filter   = ['flag_type', 'resolved']
    search_fields = ['description', 'flagged_by__username']


@admin.register(PolicyDecision)
class PolicyDecisionAdmin(admin.ModelAdmin):
    list_display  = ['chapter', 'decided_by', 'ruling', 'sets_precedent', 'decided_at']
    list_filter   = ['ruling', 'sets_precedent']
    search_fields = ['reasoning', 'decided_by__username']


@admin.register(EditorialPolicy)
class EditorialPolicyAdmin(admin.ModelAdmin):
    list_display  = ['title', 'version', 'status', 'proposed_by', 'approved_by', 'published_at']
    list_filter   = ['status']
    search_fields = ['title', 'content']


from .models import EditorInvite

@admin.register(EditorInvite)
class EditorInviteAdmin(admin.ModelAdmin):
    list_display  = ['email', 'role', 'status', 'invited_by', 'supervisor',
                     'created_at', 'expires_at', 'accepted_by']
    list_filter   = ['role', 'status']
    search_fields = ['email', 'invited_by__username']
    readonly_fields = ['token', 'created_at', 'accepted_at', 'accepted_by']
    actions       = ['revoke_selected']

    def revoke_selected(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='revoked')
        self.message_user(request, f'{updated} invite(s) revoked.')
    revoke_selected.short_description = 'Revoke selected pending invites'


@admin.register(SystemNotice)
class SystemNoticeAdmin(admin.ModelAdmin):
    list_display  = ['notice_type', 'message', 'is_active', 'created_at']
    list_filter   = ['notice_type', 'is_active']
    list_editable = ['is_active']


@admin.register(PromotionSlotConfig)
class PromotionSlotConfigAdmin(admin.ModelAdmin):
    list_display  = ['category', 'se', 'slot_limit', 'set_by', 'updated_at']
    list_filter   = ['category']
    list_editable = ['slot_limit']
    search_fields = ['se__username', 'set_by__username']
    raw_id_fields = ['se', 'set_by']


@admin.register(StoryPromotion)
class StoryPromotionAdmin(admin.ModelAdmin):
    list_display  = ['story', 'se', 'category', 'status', 'starts_at', 'expires_at', 'queue_position', 'reminder_sent']
    list_filter   = ['category', 'status']
    list_editable = ['status', 'queue_position']
    search_fields = ['story__title', 'se__username']
    raw_id_fields = ['se', 'story']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'expires_at'


class ExploreTabPinInline(admin.TabularInline):
    model           = ExploreTabPin
    extra           = 0
    fields          = ['tab', 'section', 'story', 'order', 'is_active', 'pinned_by', 'pinned_at']
    readonly_fields = ['pinned_at']
    raw_id_fields   = ['story', 'pinned_by']


@admin.register(SEPromotionRequest)
class SEPromotionRequestAdmin(admin.ModelAdmin):
    list_display   = ['story', 'se', 'tab', 'section', 'status', 'reviewed_by', 'created_at']
    list_filter    = ['status', 'tab']
    search_fields  = ['story__title', 'se__username', 'section']
    readonly_fields = ['created_at', 'reviewed_at']
    raw_id_fields  = ['se', 'story', 'reviewed_by']
    actions        = ['approve_requests', 'reject_requests']
    inlines        = [ExploreTabPinInline]

    def approve_requests(self, request, queryset):
        approved = 0
        for req in queryset.filter(status=SEPromotionRequest.STATUS_PENDING):
            req.status      = SEPromotionRequest.STATUS_APPROVED
            req.reviewed_by = request.user
            req.reviewed_at = timezone.now()
            req.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            ExploreTabPin.objects.update_or_create(
                tab=req.tab, section=req.section, story=req.story,
                defaults={
                    'pinned_by':      request.user,
                    'source_request': req,
                    'is_active':      True,
                    'order':          0,
                },
            )
            approved += 1
        self.message_user(request, f'{approved} request(s) approved and pinned.')
    approve_requests.short_description = 'Approve and pin selected requests'

    def reject_requests(self, request, queryset):
        updated = queryset.filter(status=SEPromotionRequest.STATUS_PENDING).update(
            status=SEPromotionRequest.STATUS_REJECTED,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )
        self.message_user(request, f'{updated} request(s) rejected.')
    reject_requests.short_description = 'Reject selected requests'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Allow any user as reviewed_by (superadmin may not have role='ce')
        if db_field.name == 'reviewed_by':
            kwargs['queryset'] = db_field.related_model.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ExploreTabPin)
class ExploreTabPinAdmin(admin.ModelAdmin):
    list_display   = ['story', 'tab', 'section', 'order', 'is_active', 'pinned_by', 'pinned_at']
    list_filter    = ['tab', 'section', 'is_active']
    list_editable  = ['order', 'is_active']
    search_fields  = ['story__title', 'pinned_by__username']
    raw_id_fields  = ['story', 'pinned_by', 'source_request']
    readonly_fields = ['pinned_at']
    actions        = ['activate_pins', 'deactivate_pins']

    def activate_pins(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} pin(s) activated.')
    activate_pins.short_description = 'Activate selected pins'

    def deactivate_pins(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} pin(s) deactivated.')
    deactivate_pins.short_description = 'Deactivate selected pins'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Allow any user as pinned_by — superadmin may not have role='ce'
        if db_field.name == 'pinned_by':
            kwargs['queryset'] = db_field.related_model.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

