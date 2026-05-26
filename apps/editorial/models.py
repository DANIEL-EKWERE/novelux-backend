# """
# Novelux Editorial Models
# ========================
# Implements the 3-tier editorial hierarchy:

#   CE (Chief Editor)
#     └── SE (Senior Editor)          — overseen by CE
#           └── AE (Assistant Editor) — managed by SE
#                 └── Author           — assigned to AE

# Flow:
#   Author submits chapter → AE reviews → AE can approve / request revision / flag
#   AE escalates → SE reviews → SE can approve / remove / escalate
#   SE escalates → CE makes final decision
# """

# from django.db import models
# from django.contrib.auth import get_user_model
# from django.utils import timezone

# User = get_user_model()


# # ─── 1. Editor hierarchy ─────────────────────────────────────────────────────

# class EditorAssignment(models.Model):
#     """
#     Tracks which SE a given AE reports to, and which CE oversees a given SE.
#     A CE user has no supervisor. An AE must have a supervisor SE.
#     """
#     editor      = models.OneToOneField(
#         User, on_delete=models.CASCADE,
#         related_name='editorial_assignment',
#         help_text='The AE or SE being assigned',
#     )
#     supervisor  = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='subordinates',
#         help_text='SE supervising this AE — or CE supervising this SE',
#     )
#     assigned_at = models.DateTimeField(auto_now_add=True)
#     notes       = models.TextField(blank=True)

#     class Meta:
#         db_table = 'editor_assignments'

#     def __str__(self):
#         sup = self.supervisor.username if self.supervisor else 'none'
#         return f'{self.editor.username} ({self.editor.role}) → {sup}'


# class AuthorEditorLink(models.Model):
#     """
#     Links an author to the AE responsible for reviewing their chapters.

#     How the link is formed:
#       - EDITOR_CODE : author entered the AE's invite code at signup or in settings
#       - MANUAL      : a CE/admin linked them directly
#       - AUTO        : system auto-assigned by lowest-load AE (no code provided)

#     The supervising SE and CE are resolved dynamically via EditorAssignment.
#     """

#     LINK_CODE   = 'editor_code'
#     LINK_MANUAL = 'manual'
#     LINK_AUTO   = 'auto'
#     LINK_CHOICES = [
#         (LINK_CODE,   'Author used editor invite code'),
#         (LINK_MANUAL, 'Manually assigned by CE / admin'),
#         (LINK_AUTO,   'Auto-assigned by system'),
#     ]

#     author      = models.OneToOneField(
#         User, on_delete=models.CASCADE,
#         related_name='editor_link',
#         limit_choices_to={'role': 'author'},
#     )
#     assigned_ae = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='assigned_authors',
#         limit_choices_to={'role': 'ae'},
#     )
#     link_method = models.CharField(
#         max_length=15, choices=LINK_CHOICES, default=LINK_CODE,
#     )
#     assigned_at = models.DateTimeField(auto_now_add=True)
#     notes       = models.TextField(blank=True)

#     class Meta:
#         db_table = 'author_editor_links'

#     # ── helpers ───────────────────────────────────────────────────────────────

#     def get_supervising_se(self):
#         """Return the SE that supervises the assigned AE, if any."""
#         if not self.assigned_ae:
#             return None
#         try:
#             return self.assigned_ae.editorial_assignment.supervisor
#         except EditorAssignment.DoesNotExist:
#             return None

#     def get_ce(self):
#         """Return the CE overseeing the SE chain, if any."""
#         se = self.get_supervising_se()
#         if not se:
#             return None
#         try:
#             return se.editorial_assignment.supervisor
#         except EditorAssignment.DoesNotExist:
#             return None

#     # ── factories ─────────────────────────────────────────────────────────────

#     @classmethod
#     def link_by_code(cls, author, code):
#         """
#         Link an author to an AE using the AE's invite code.
#         Returns (link, error_message).  error_message is None on success.

#         Usage:
#             link, err = AuthorEditorLink.link_by_code(request.user, 'AX3K9PLM')
#             if err:
#                 return Response({'error': err}, status=400)
#         """
#         if author.role != 'author':
#             return None, 'Only author accounts can use an editor code.'

#         code = code.strip().upper()
#         if not code:
#             return None, 'Editor code is required.'

#         try:
#             ae = User.objects.get(editor_code=code, role='ae')
#         except User.DoesNotExist:
#             return None, 'Invalid editor code. Double-check with your editor.'

#         link, _ = cls.objects.update_or_create(
#             author=author,
#             defaults={
#                 'assigned_ae': ae,
#                 'link_method': cls.LINK_CODE,
#                 'notes':       f'Linked via code {code}',
#             },
#         )
#         return link, None

#     @classmethod
#     def auto_assign(cls, author):
#         """
#         Assign the AE with the fewest current authors.
#         Used when an author does not provide an editor code at signup.
#         Returns (link, None) or (None, error_message).
#         """
#         from django.db.models import Count
#         ae = (
#             User.objects
#             .filter(role='ae')
#             .annotate(author_count=Count('assigned_authors'))
#             .order_by('author_count')
#             .first()
#         )
#         if not ae:
#             return None, 'No editors available right now.'

#         link, _ = cls.objects.update_or_create(
#             author=author,
#             defaults={
#                 'assigned_ae': ae,
#                 'link_method': cls.LINK_AUTO,
#                 'notes':       'Auto-assigned at signup (no editor code provided).',
#             },
#         )
#         return link, None

#     def __str__(self):
#         ae = self.assigned_ae.username if self.assigned_ae else 'unassigned'
#         return f'{self.author.username} -> AE:{ae} [{self.link_method}]'


# # ─── 2. Chapter editorial review ─────────────────────────────────────────────

# class ChapterReview(models.Model):
#     """
#     An editorial review ticket created when an author submits a chapter.
#     Tracks the full AE → SE → CE escalation trail.
#     """

#     # Status machine
#     STATUS_PENDING        = 'pending'       # waiting for AE
#     STATUS_AE_REVIEWING   = 'ae_reviewing'  # AE has opened it
#     STATUS_AE_APPROVED    = 'ae_approved'   # AE signed off
#     STATUS_AE_REVISION    = 'ae_revision'   # AE requested revision
#     STATUS_AE_ESCALATED   = 'ae_escalated'  # AE sent to SE
#     STATUS_SE_REVIEWING   = 'se_reviewing'
#     STATUS_SE_APPROVED    = 'se_approved'
#     STATUS_SE_REVISION    = 'se_revision'
#     STATUS_SE_ESCALATED   = 'se_escalated'  # SE sent to CE
#     STATUS_CE_REVIEWING   = 'ce_reviewing'
#     STATUS_CE_APPROVED    = 'ce_approved'
#     STATUS_CE_REVISION    = 'ce_revision'
#     STATUS_REMOVED        = 'removed'
#     STATUS_AUTHOR_SUSPENDED = 'author_suspended'

#     STATUS_CHOICES = [
#         (STATUS_PENDING,          'Pending'),
#         (STATUS_AE_REVIEWING,     'AE Reviewing'),
#         (STATUS_AE_APPROVED,      'AE Approved'),
#         (STATUS_AE_REVISION,      'AE Requested Revision'),
#         (STATUS_AE_ESCALATED,     'Escalated to SE'),
#         (STATUS_SE_REVIEWING,     'SE Reviewing'),
#         (STATUS_SE_APPROVED,      'SE Approved'),
#         (STATUS_SE_REVISION,      'SE Requested Major Revision'),
#         (STATUS_SE_ESCALATED,     'Escalated to CE'),
#         (STATUS_CE_REVIEWING,     'CE Reviewing'),
#         (STATUS_CE_APPROVED,      'CE Approved'),
#         (STATUS_CE_REVISION,      'CE Requested Revision'),
#         (STATUS_REMOVED,          'Content Removed'),
#         (STATUS_AUTHOR_SUSPENDED, 'Author Suspended'),
#     ]

#     # Priority
#     PRIORITY_LOW    = 'low'
#     PRIORITY_NORMAL = 'normal'
#     PRIORITY_URGENT = 'urgent'
#     PRIORITY_CHOICES = [
#         (PRIORITY_LOW,    'Low'),
#         (PRIORITY_NORMAL, 'Normal'),
#         (PRIORITY_URGENT, 'Urgent'),
#     ]

#     chapter         = models.ForeignKey(
#         'chapters.Chapter', on_delete=models.CASCADE,
#         related_name='editorial_reviews',
#     )
#     author          = models.ForeignKey(
#         User, on_delete=models.CASCADE,
#         related_name='chapter_submissions',
#         limit_choices_to={'role': 'author'},
#     )
#     assigned_ae     = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='ae_reviews',
#         limit_choices_to={'role': 'ae'},
#     )
#     assigned_se     = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='se_reviews',
#         limit_choices_to={'role': 'se'},
#     )
#     assigned_ce     = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='ce_reviews',
#         limit_choices_to={'role': 'ce'},
#     )

#     status          = models.CharField(
#         max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING,
#         db_index=True,
#     )
#     priority        = models.CharField(
#         max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL,
#     )
#     submitted_at    = models.DateTimeField(auto_now_add=True)
#     updated_at      = models.DateTimeField(auto_now=True)
#     resolved_at     = models.DateTimeField(null=True, blank=True)

#     # Scores (AE fills these in)
#     pacing_score        = models.PositiveSmallIntegerField(null=True, blank=True)
#     dialogue_score      = models.PositiveSmallIntegerField(null=True, blank=True)
#     consistency_score   = models.PositiveSmallIntegerField(null=True, blank=True)

#     class Meta:
#         db_table = 'chapter_reviews'
#         ordering = ['-submitted_at']
#         indexes  = [
#             models.Index(fields=['status', 'assigned_ae']),
#             models.Index(fields=['status', 'assigned_se']),
#             models.Index(fields=['status', 'assigned_ce']),
#         ]

#     def __str__(self):
#         return f'Review: {self.chapter} [{self.status}]'

#     def mark_resolved(self):
#         self.resolved_at = timezone.now()
#         self.save(update_fields=['resolved_at'])

#     @property
#     def is_open(self):
#         return self.status not in [
#             self.STATUS_AE_APPROVED, self.STATUS_SE_APPROVED,
#             self.STATUS_CE_APPROVED, self.STATUS_REMOVED,
#             self.STATUS_AUTHOR_SUSPENDED,
#         ]

#     @property
#     def turnaround_hours(self):
#         end = self.resolved_at or timezone.now()
#         delta = end - self.submitted_at
#         return round(delta.total_seconds() / 3600, 1)


# # ─── 3. Editorial notes & comments ───────────────────────────────────────────

# class EditorialNote(models.Model):
#     """A comment/note left by an editor on a chapter review."""

#     NOTE_TYPE_GENERAL     = 'general'
#     NOTE_TYPE_STYLE       = 'style'
#     NOTE_TYPE_CONTINUITY  = 'continuity'
#     NOTE_TYPE_POLICY      = 'policy'
#     NOTE_TYPE_DECISION    = 'decision'
#     NOTE_TYPE_CHOICES = [
#         (NOTE_TYPE_GENERAL,    'General'),
#         (NOTE_TYPE_STYLE,      'Style Suggestion'),
#         (NOTE_TYPE_CONTINUITY, 'Continuity Issue'),
#         (NOTE_TYPE_POLICY,     'Policy Concern'),
#         (NOTE_TYPE_DECISION,   'Decision Record'),
#     ]

#     review      = models.ForeignKey(
#         ChapterReview, on_delete=models.CASCADE,
#         related_name='notes',
#     )
#     author      = models.ForeignKey(
#         User, on_delete=models.CASCADE,
#         related_name='editorial_notes',
#     )
#     note_type   = models.CharField(
#         max_length=15, choices=NOTE_TYPE_CHOICES, default=NOTE_TYPE_GENERAL,
#     )
#     content     = models.TextField()
#     paragraph   = models.PositiveSmallIntegerField(
#         null=True, blank=True,
#         help_text='Paragraph index the note refers to',
#     )
#     is_resolved = models.BooleanField(default=False)
#     created_at  = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'editorial_notes'
#         ordering = ['created_at']

#     def __str__(self):
#         return f'Note by {self.author.username} on {self.review}'


# # ─── 4. Content flags ─────────────────────────────────────────────────────────

# class ContentFlag(models.Model):
#     FLAG_MATURE     = 'mature'
#     FLAG_VIOLENCE   = 'violence'
#     FLAG_PLAGIARISM = 'plagiarism'
#     FLAG_QUALITY    = 'quality'
#     FLAG_SPAM       = 'spam'
#     FLAG_OTHER      = 'other'
#     FLAG_CHOICES = [
#         (FLAG_MATURE,     'Mature Content'),
#         (FLAG_VIOLENCE,   'Violence'),
#         (FLAG_PLAGIARISM, 'Plagiarism'),
#         (FLAG_QUALITY,    'Quality / Style'),
#         (FLAG_SPAM,       'Spam'),
#         (FLAG_OTHER,      'Other'),
#     ]

#     review      = models.ForeignKey(
#         ChapterReview, on_delete=models.CASCADE,
#         related_name='flags',
#     )
#     flagged_by  = models.ForeignKey(
#         User, on_delete=models.CASCADE,
#         related_name='raised_flags',
#     )
#     flag_type   = models.CharField(max_length=15, choices=FLAG_CHOICES)
#     description = models.TextField()
#     created_at  = models.DateTimeField(auto_now_add=True)
#     resolved    = models.BooleanField(default=False)
#     resolved_by = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='resolved_flags',
#     )
#     resolution_note = models.TextField(blank=True)

#     class Meta:
#         db_table = 'content_flags'
#         ordering = ['-created_at']

#     def __str__(self):
#         return f'Flag [{self.flag_type}] on {self.review}'


# # ─── 5. CE policy decisions ───────────────────────────────────────────────────

# class PolicyDecision(models.Model):
#     """Formal CE ruling on an escalated review. Sets precedent."""

#     RULING_APPROVE      = 'approve'
#     RULING_APPROVE_GATE = 'approve_age_gate'
#     RULING_REVISION     = 'revision'
#     RULING_REMOVE       = 'remove'
#     RULING_SUSPEND      = 'suspend_author'
#     RULING_CHOICES = [
#         (RULING_APPROVE,      'Approved'),
#         (RULING_APPROVE_GATE, 'Approved with Age-Gate'),
#         (RULING_REVISION,     'Major Revision Required'),
#         (RULING_REMOVE,       'Content Removed'),
#         (RULING_SUSPEND,      'Author Suspended'),
#     ]

#     review          = models.OneToOneField(
#         ChapterReview, on_delete=models.CASCADE,
#         related_name='policy_decision',
#     )
#     decided_by      = models.ForeignKey(
#         User, on_delete=models.CASCADE,
#         related_name='policy_decisions',
#         limit_choices_to={'role': 'ce'},
#     )
#     ruling          = models.CharField(max_length=20, choices=RULING_CHOICES)
#     reasoning       = models.TextField()
#     sets_precedent  = models.BooleanField(
#         default=False,
#         help_text='If true, this decision will be referenced in future policy guidance',
#     )
#     notified_se     = models.BooleanField(default=False)
#     decided_at      = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'policy_decisions'
#         ordering = ['-decided_at']

#     def __str__(self):
#         return f'CE Decision [{self.ruling}] on {self.review}'


# # ─── 6. Editorial guidelines policy documents ─────────────────────────────────

# class EditorialPolicy(models.Model):
#     STATUS_DRAFT    = 'draft'
#     STATUS_ACTIVE   = 'active'
#     STATUS_REVIEW   = 'under_review'
#     STATUS_ARCHIVED = 'archived'
#     STATUS_CHOICES = [
#         (STATUS_DRAFT,    'Draft'),
#         (STATUS_ACTIVE,   'Active'),
#         (STATUS_REVIEW,   'Under Review'),
#         (STATUS_ARCHIVED, 'Archived'),
#     ]

#     title       = models.CharField(max_length=255)
#     version     = models.CharField(max_length=20, default='1.0')
#     content     = models.TextField()
#     status      = models.CharField(
#         max_length=15, choices=STATUS_CHOICES, default=STATUS_DRAFT,
#     )
#     proposed_by = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True,
#         related_name='proposed_policies',
#     )
#     approved_by = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='approved_policies',
#         limit_choices_to={'role': 'ce'},
#     )
#     created_at  = models.DateTimeField(auto_now_add=True)
#     published_at = models.DateTimeField(null=True, blank=True)
#     notes       = models.TextField(blank=True)

#     class Meta:
#         db_table  = 'editorial_policies'
#         ordering  = ['-created_at']
#         verbose_name_plural = 'Editorial Policies'

#     def __str__(self):
#         return f'{self.title} v{self.version} [{self.status}]'


# # ─── 8. Editor Onboarding Invites ─────────────────────────────────────────────

# class EditorInvite(models.Model):
#     """
#     A CE-generated invite that allows a specific person to register as
#     an AE or SE without needing admin access.

#     Flow:
#       1. CE fills in (email, role, supervisor) on CE dashboard → invite created
#       2. System sends email with link: /editorial/invite/<token>/
#       3. Invitee opens link → pre-filled registration form (role locked)
#       4. On submit → account created, EditorAssignment created,
#          editor_code generated (AEs only)
#     """

#     ROLE_AE = 'ae'
#     ROLE_SE = 'se'
#     ROLE_CHOICES = [
#         (ROLE_AE, 'Assistant Editor'),
#         (ROLE_SE, 'Senior Editor'),
#     ]

#     STATUS_PENDING  = 'pending'
#     STATUS_ACCEPTED = 'accepted'
#     STATUS_EXPIRED  = 'expired'
#     STATUS_REVOKED  = 'revoked'
#     STATUS_CHOICES  = [
#         (STATUS_PENDING,  'Pending'),
#         (STATUS_ACCEPTED, 'Accepted'),
#         (STATUS_EXPIRED,  'Expired'),
#         (STATUS_REVOKED,  'Revoked'),
#     ]

#     token       = models.CharField(
#         max_length=64, unique=True, db_index=True,
#         help_text='One-time registration token sent to the invitee.',
#     )
#     email       = models.EmailField(
#         help_text='Email address the invite was sent to.',
#     )
#     role        = models.CharField(max_length=5, choices=ROLE_CHOICES)
#     supervisor  = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='issued_invites',
#         help_text='For AE invites: the SE they will report to. For SE invites: the CE.',
#     )
#     invited_by  = models.ForeignKey(
#         User, on_delete=models.CASCADE,
#         related_name='created_invites',
#         help_text='The CE who created this invite.',
#     )
#     status      = models.CharField(
#         max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING,
#     )
#     created_at  = models.DateTimeField(auto_now_add=True)
#     expires_at  = models.DateTimeField(
#         help_text='Invite expires 7 days after creation.',
#     )
#     accepted_at = models.DateTimeField(null=True, blank=True)
#     accepted_by = models.ForeignKey(
#         User, on_delete=models.SET_NULL, null=True, blank=True,
#         related_name='accepted_invite',
#     )
#     notes       = models.TextField(blank=True)

#     class Meta:
#         db_table  = 'editor_invites'
#         ordering  = ['-created_at']

#     def __str__(self):
#         return f'Invite [{self.role}] → {self.email} [{self.status}]'

#     @property
#     def is_valid(self):
#         from django.utils import timezone as _tz
#         return (
#             self.status == self.STATUS_PENDING
#             and self.expires_at > _tz.now()
#         )

#     @classmethod
#     def create_invite(cls, email, role, invited_by, supervisor=None, notes=''):
#         """
#         Factory method. Generates a secure token and sets expiry.
#         Call this from the CE dashboard view.
#         """
#         import secrets as _s
#         from django.utils import timezone as _tz
#         import datetime as _dt

#         token = _s.token_urlsafe(32)
#         invite = cls.objects.create(
#             token      = token,
#             email      = email.strip().lower(),
#             role       = role,
#             supervisor = supervisor,
#             invited_by = invited_by,
#             expires_at = _tz.now() + _dt.timedelta(days=7),
#             notes      = notes,
#         )
#         return invite

#     def accept(self, user):
#         """
#         Called after the invited user successfully registers.
#         Sets up EditorAssignment and generates AE code.
#         """
#         from django.utils import timezone as _tz
#         self.status      = self.STATUS_ACCEPTED
#         self.accepted_at = _tz.now()
#         self.accepted_by = user
#         self.save(update_fields=['status', 'accepted_at', 'accepted_by'])

#         # Set correct role on user
#         user.role = self.role
#         user.save(update_fields=['role'])

#         # Create hierarchy assignment
#         if self.supervisor:
#             EditorAssignment.objects.update_or_create(
#                 editor=user,
#                 defaults={'supervisor': self.supervisor},
#             )

#         # Generate editor code for AEs
#         if self.role == self.ROLE_AE:
#             user.generate_editor_code()

#         return user


"""
Novelux Editorial Models
========================
Implements the 3-tier editorial hierarchy:

  CE (Chief Editor)
    └── SE (Senior Editor)       — reviews chapters, mentors authors, sends to CE
          └── AE (Acquisition Editor) — talent scout, recruits authors to platform

Flow for NEW authors (no contract):
  Author uploads chapters → threshold hit → SE review queue →
  SE approves → CE sends contract → author signs →
  all held chapters published → future chapters auto-published

Flow for CONTRACTED authors:
  Author uploads chapter → immediately published (no review needed)

Note: ChapterReview model has been removed. All editorial state now
lives directly on apps.chapters.Chapter.status. This avoids data
duplication and keeps the workflow simple.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


# ─── 1. Editor hierarchy ─────────────────────────────────────────────────────

class EditorAssignment(models.Model):
    """
    Tracks which SE a given AE reports to, and which CE oversees a given SE.
    A CE user has no supervisor. An AE must have a supervisor SE.
    """
    editor      = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='editorial_assignment',
        help_text='The AE or SE being assigned',
    )
    supervisor  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subordinates',
        help_text='SE supervising this AE — or CE supervising this SE',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes       = models.TextField(blank=True)

    class Meta:
        db_table = 'editor_assignments'

    def __str__(self):
        sup = self.supervisor.username if self.supervisor else 'none'
        return f'{self.editor.username} ({self.editor.role}) → {sup}'


class AuthorEditorLink(models.Model):
    """
    Links an author to the editor (AE or SE) responsible for their work.

    How the link is formed:
      - EDITOR_CODE : author entered the editor's invite code
      - MANUAL      : a CE/admin linked them directly
      - AUTO        : system auto-assigned (no code provided)

    Both AE and SE can recruit authors — SE can source their own authors
    and review their chapters directly without going through an AE.
    """

    LINK_CODE   = 'editor_code'
    LINK_MANUAL = 'manual'
    LINK_AUTO   = 'auto'
    LINK_CHOICES = [
        (LINK_CODE,   'Author used editor invite code'),
        (LINK_MANUAL, 'Manually assigned by CE / admin'),
        (LINK_AUTO,   'Auto-assigned by system'),
    ]

    author      = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='editor_link',
        limit_choices_to={'role': 'author'},
    )
    # SE link — the Senior Editor who recruited or was assigned this author
    assigned_se = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sourced_authors',
        limit_choices_to={'role': 'se'},
        help_text='The SE who invited or was assigned this author.',
    )
    link_method = models.CharField(
        max_length=15, choices=LINK_CHOICES, default=LINK_CODE,
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes       = models.TextField(blank=True)

    class Meta:
        db_table = 'author_editor_links'

    # ── helpers ───────────────────────────────────────────────────────────────

    def get_supervising_se(self):
        """Return the SE for this author."""
        return self.assigned_se

    def get_ce(self):
        """Return the CE overseeing the SE, if any."""
        se = self.assigned_se
        if not se:
            return None
        try:
            return se.editorial_assignment.supervisor
        except EditorAssignment.DoesNotExist:
            return None

    # ── factories ─────────────────────────────────────────────────────────────

    @classmethod
    def link_by_code(cls, author, code):
        """
        Link an author to an SE using that editor's invite code.
        Returns (link, error_message). error_message is None on success.
        """
        if author.role != 'author':
            return None, 'Only author accounts can use an editor code.'

        code = code.strip().upper()
        if not code:
            return None, 'Editor code is required.'

        try:
            editor = User.objects.get(editor_code=code, role='se')
        except User.DoesNotExist:
            return None, 'Invalid editor code. Double-check the code with your editor.'

        link, _ = cls.objects.update_or_create(
            author=author,
            defaults={
                'assigned_se': editor,
                'link_method': cls.LINK_CODE,
                'notes':       f'Linked via SE code {code}',
            },
        )
        return link, None

    @classmethod
    def auto_assign(cls, author):
        """
        Assign the SE with the fewest current authors.
        """
        from django.db.models import Count

        se = (
            User.objects
            .filter(role='se')
            .annotate(author_count=Count('sourced_authors'))
            .order_by('author_count')
            .first()
        )
        if not se:
            return None, 'No Senior Editors available right now.'

        link, _ = cls.objects.update_or_create(
            author=author,
            defaults={
                'assigned_se': se,
                'link_method': cls.LINK_AUTO,
                'notes':       'Auto-assigned SE at signup.',
            },
        )
        return link, None

    def __str__(self):
        se = self.assigned_se.username if self.assigned_se else '—'
        return f'{self.author.username} → SE:{se} [{self.link_method}]'


# ─── 2. Editorial notes ───────────────────────────────────────────────────────

class EditorialNote(models.Model):
    """
    A note/feedback left by an SE on a chapter.
    Visible to the author when status is se_revision or se_approved.
    """

    NOTE_TYPE_GENERAL     = 'general'
    NOTE_TYPE_STYLE       = 'style'
    NOTE_TYPE_CONTINUITY  = 'continuity'
    NOTE_TYPE_POLICY      = 'policy'
    NOTE_TYPE_CHOICES = [
        (NOTE_TYPE_GENERAL,    'General'),
        (NOTE_TYPE_STYLE,      'Style Suggestion'),
        (NOTE_TYPE_CONTINUITY, 'Continuity Issue'),
        (NOTE_TYPE_POLICY,     'Policy Concern'),
    ]

    chapter     = models.ForeignKey(
        'chapters.Chapter', on_delete=models.CASCADE,
        related_name='editorial_notes',null=True, blank=True,
    )
    written_by  = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='written_editorial_notes',null=True, blank=True,
    )
    note_type   = models.CharField(
        max_length=15, choices=NOTE_TYPE_CHOICES, default=NOTE_TYPE_GENERAL,
    )
    content     = models.TextField()
    paragraph   = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text='Paragraph index the note refers to',
    )
    is_resolved = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'editorial_notes'
        ordering = ['created_at']

    def __str__(self):
        return f'Note by {self.written_by.username} on Ch.{self.chapter_id}'


# ─── 3. Content flags ─────────────────────────────────────────────────────────

class ContentFlag(models.Model):
    """SE or AE can flag a chapter for policy violations, plagiarism, etc."""

    FLAG_MATURE     = 'mature'
    FLAG_VIOLENCE   = 'violence'
    FLAG_PLAGIARISM = 'plagiarism'
    FLAG_QUALITY    = 'quality'
    FLAG_SPAM       = 'spam'
    FLAG_OTHER      = 'other'
    FLAG_CHOICES = [
        (FLAG_MATURE,     'Mature Content'),
        (FLAG_VIOLENCE,   'Violence'),
        (FLAG_PLAGIARISM, 'Plagiarism'),
        (FLAG_QUALITY,    'Quality / Style'),
        (FLAG_SPAM,       'Spam'),
        (FLAG_OTHER,      'Other'),
    ]

    chapter     = models.ForeignKey(
        'chapters.Chapter', on_delete=models.CASCADE,
        related_name='content_flags',null=True, blank=True,
    )
    flagged_by  = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='raised_flags',
    )
    flag_type   = models.CharField(max_length=15, choices=FLAG_CHOICES)
    description = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)
    resolved    = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resolved_flags',
    )
    resolution_note = models.TextField(blank=True)

    class Meta:
        db_table = 'content_flags'
        ordering = ['-created_at']

    def __str__(self):
        return f'Flag [{self.flag_type}] on Ch.{self.chapter_id}'


# ─── 4. CE policy decisions ───────────────────────────────────────────────────

class PolicyDecision(models.Model):
    """Formal CE ruling on a flagged or escalated chapter."""

    RULING_APPROVE      = 'approve'
    RULING_APPROVE_GATE = 'approve_age_gate'
    RULING_REVISION     = 'revision'
    RULING_REMOVE       = 'remove'
    RULING_SUSPEND      = 'suspend_author'
    RULING_CHOICES = [
        (RULING_APPROVE,      'Approved'),
        (RULING_APPROVE_GATE, 'Approved with Age-Gate'),
        (RULING_REVISION,     'Major Revision Required'),
        (RULING_REMOVE,       'Content Removed'),
        (RULING_SUSPEND,      'Author Suspended'),
    ]

    chapter         = models.OneToOneField(
        'chapters.Chapter', on_delete=models.CASCADE,null=True, blank=True,
        related_name='policy_decision',
    )
    decided_by      = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='policy_decisions',
        limit_choices_to={'role': 'ce'},
    )
    ruling          = models.CharField(max_length=20, choices=RULING_CHOICES)
    reasoning       = models.TextField()
    sets_precedent  = models.BooleanField(
        default=False,
        help_text='If true, this decision will be referenced in future policy guidance',
    )
    decided_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'policy_decisions'
        ordering = ['-decided_at']

    def __str__(self):
        return f'CE Decision [{self.ruling}] on Ch.{self.chapter_id}'


# ─── 5. Editorial guidelines ──────────────────────────────────────────────────

class EditorialPolicy(models.Model):
    STATUS_DRAFT    = 'draft'
    STATUS_ACTIVE   = 'active'
    STATUS_REVIEW   = 'under_review'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_DRAFT,    'Draft'),
        (STATUS_ACTIVE,   'Active'),
        (STATUS_REVIEW,   'Under Review'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    title       = models.CharField(max_length=255)
    version     = models.CharField(max_length=20, default='1.0')
    content     = models.TextField()
    status      = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default=STATUS_DRAFT,
    )
    proposed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='proposed_policies',
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_policies',
        limit_choices_to={'role': 'ce'},
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    notes       = models.TextField(blank=True)

    class Meta:
        db_table  = 'editorial_policies'
        ordering  = ['-created_at']
        verbose_name_plural = 'Editorial Policies'

    def __str__(self):
        return f'{self.title} v{self.version} [{self.status}]'


# ─── 8. Editor Onboarding Invites ─────────────────────────────────────────────

class EditorInvite(models.Model):
    """
    A CE-generated invite that allows a specific person to register as
    an AE or SE without needing admin access.

    Flow:
      1. CE fills in (email, role, supervisor) on CE dashboard → invite created
      2. System sends email with link: /editorial/invite/<token>/
      3. Invitee opens link → pre-filled registration form (role locked)
      4. On submit → account created, EditorAssignment created,
         editor_code generated (AEs only)
    """

    ROLE_SE = 'se'
    ROLE_CHOICES = [
        (ROLE_SE, 'Senior Editor'),
    ]

    STATUS_PENDING  = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_EXPIRED  = 'expired'
    STATUS_REVOKED  = 'revoked'
    STATUS_CHOICES  = [
        (STATUS_PENDING,  'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_EXPIRED,  'Expired'),
        (STATUS_REVOKED,  'Revoked'),
    ]

    token       = models.CharField(
        max_length=64, unique=True, db_index=True,
        help_text='One-time registration token sent to the invitee.',
    )
    email       = models.EmailField(
        help_text='Email address the invite was sent to.',
    )
    role        = models.CharField(max_length=5, choices=ROLE_CHOICES)
    supervisor  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='issued_invites',
        help_text='For AE invites: the SE they will report to. For SE invites: the CE.',
    )
    invited_by  = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='created_invites',
        help_text='The CE who created this invite.',
    )
    status      = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING,
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField(
        help_text='Invite expires 7 days after creation.',
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='accepted_invite',
    )
    notes       = models.TextField(blank=True)

    class Meta:
        db_table  = 'editor_invites'
        ordering  = ['-created_at']

    def __str__(self):
        return f'Invite [{self.role}] → {self.email} [{self.status}]'

    @property
    def is_valid(self):
        from django.utils import timezone as _tz
        return (
            self.status == self.STATUS_PENDING
            and self.expires_at > _tz.now()
        )

    @classmethod
    def create_invite(cls, email, role, invited_by, supervisor=None, notes=''):
        """
        Factory method. Generates a secure token and sets expiry.
        Call this from the CE dashboard view.
        """
        import secrets as _s
        from django.utils import timezone as _tz
        import datetime as _dt

        token = _s.token_urlsafe(32)
        invite = cls.objects.create(
            token      = token,
            email      = email.strip().lower(),
            role       = role,
            supervisor = supervisor,
            invited_by = invited_by,
            expires_at = _tz.now() + _dt.timedelta(days=7),
            notes      = notes,
        )
        return invite

    def accept(self, user):
        """
        Called after the invited user successfully registers.
        Sets up EditorAssignment and generates AE code.
        """
        from django.utils import timezone as _tz
        self.status      = self.STATUS_ACCEPTED
        self.accepted_at = _tz.now()
        self.accepted_by = user
        self.save(update_fields=['status', 'accepted_at', 'accepted_by'])

        # Set correct role on user
        user.role = self.role
        user.save(update_fields=['role'])

        # Create hierarchy assignment
        if self.supervisor:
            EditorAssignment.objects.update_or_create(
                editor=user,
                defaults={'supervisor': self.supervisor},
            )

        # Generate editor code for SE so they can share it with authors
        user.generate_editor_code()

        return user


class ContractApplication(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_SE_REVIEW = 'se_reviewing'
    STATUS_SE_APPROVED = 'se_approved'
    STATUS_REJECTED  = 'rejected'
    STATUS_CONTRACT_SENT = 'contract_sent'
    STATUS_SIGNED    = 'signed'

    STATUS_CHOICES = [
        ('pending',       'Pending'),
        ('se_reviewing',  'SE Reviewing'),
        ('se_approved',   'SE Approved'),
        ('rejected',      'Rejected'),
        ('contract_sent', 'Contract Sent'),
        ('signed',        'Signed'),
    ]

    story        = models.OneToOneField('stories.Story', on_delete=models.CASCADE,
                       related_name='contract_application')
    author       = models.ForeignKey(User, on_delete=models.CASCADE,
                       related_name='contract_applications',
                       limit_choices_to={'role': 'author'})
    assigned_se  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                       related_name='contract_applications_assigned',
                       limit_choices_to={'role': 'se'})
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at   = models.DateTimeField(auto_now_add=True)
    se_reviewed_at = models.DateTimeField(null=True, blank=True)
    se_note      = models.TextField(blank=True)
    contract_sent_at = models.DateTimeField(null=True, blank=True)
    signed_at    = models.DateTimeField(null=True, blank=True)
    rejected_at  = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    contract_type = models.CharField(max_length=20,
                       choices=[('exclusive','Exclusive'),('non_exclusive','Non-Exclusive')],
                       default='non_exclusive')
    ce_signed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ce_signed_contracts',
        limit_choices_to={'role': 'ce'},
    )
    ce_signed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'contract_applications'
        ordering = ['-applied_at']
