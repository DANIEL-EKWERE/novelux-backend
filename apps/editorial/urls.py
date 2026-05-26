from django.urls import path
from . import views

app_name = 'editorial'

urlpatterns = [
    # Story-level SE review (primary flow)
    path('story-queue/', views.SEStoryQueueView.as_view(), name='story-queue'),
    path('story-queue/<slug:slug>/', views.SEStoryDetailView.as_view(), name='story-detail'),
    path('story-queue/<slug:slug>/approve/', views.se_approve_story, name='story-approve'),
    path('story-queue/<slug:slug>/reject/', views.se_reject_story, name='story-reject'),
    path('story-queue/<slug:slug>/escalate/', views.se_escalate_story_to_ce, name='story-escalate'),
    # CE story review
    path('ce-story-queue/', views.CEStoryQueueView.as_view(), name='ce-story-queue'),
    path('ce-story-queue/<slug:slug>/', views.CEStoryDetailView.as_view(), name='ce-story-detail'),
    path('ce-story-queue/<slug:slug>/send-contract/', views.ce_send_contract_story, name='ce-send-contract-story'),
    path('ce-story-queue/<slug:slug>/reject/', views.ce_reject_story, name='ce-reject-story'),
    path('ce-story-queue/<slug:slug>/note/', views.ce_edit_story_note, name='ce-story-note'),
    path('ce-story-queue/<slug:slug>/ce-sign/', views.ce_editorial_sign, name='ce-editorial-sign'),
    path('assign-author/', views.assign_author_to_se, name='assign-author'),
    path('kyc/<int:pk>/review/', views.ce_review_kyc, name='ce-review-kyc'),
    # Chapter-level queue (kept for legacy)
    path('queue/', views.EditorialQueueView.as_view(), name='queue'),
    path('reviews/<int:pk>/', views.EditorialChapterDetailView.as_view(), name='review-detail'),
    path('reviews/<int:pk>/approve/', views.se_approve, name='se-approve'),
    path('reviews/<int:pk>/request-revision/', views.se_request_revision, name='se-request-revision'),
    path('reviews/<int:pk>/remove/', views.se_remove_content, name='se-remove'),
    path('reviews/<int:pk>/escalate-to-ce/', views.se_escalate_to_ce, name='se-escalate-to-ce'),
    path('ce-escalations/', views.CEEscalationsView.as_view(), name='ce-escalations'),
    path('reviews/<int:pk>/ce-approve/', views.ce_send_contract, name='ce-send-contract'),
    path('contracts/accept/', views.accept_contract, name='accept-contract'),
    path('assignments/', views.EditorAssignmentListCreateView.as_view(), name='assignments'),
    path('author-links/', views.AuthorEditorLinkListCreateView.as_view(), name='author-links'),
    path('team/', views.EditorialTeamView.as_view(), name='team'),
    path('stats/', views.EditorialStatsView.as_view(), name='stats'),
    path('validate-code/', views.validate_editor_code, name='validate-code'),
    path('link-editor/', views.link_editor_by_code, name='link-editor'),
    path('my-editor/', views.my_editor_link, name='my-editor'),
    path('my-code/', views.my_editor_code, name='my-code'),
    path('invites/', views.invite_list, name='invite-list'),
    path('invites/<int:pk>/revoke/', views.invite_revoke, name='invite-revoke'),
    path('invites/<int:pk>/resend/', views.invite_resend, name='invite-resend'),
]