from django.contrib import admin
from .models import (
    EditorAssignment, AuthorEditorLink,
    #   ChapterReview,
    EditorialNote, ContentFlag, PolicyDecision, EditorialPolicy,
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
