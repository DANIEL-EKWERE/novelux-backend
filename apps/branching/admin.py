# apps/branching/admin.py
from django.contrib import admin
from .models import BranchPoint, BranchChoice, BranchVote


class BranchChoiceInline(admin.TabularInline):
    model  = BranchChoice
    extra  = 2
    fields = ['label', 'description', 'votes_count', 'is_winner']
    readonly_fields = ['votes_count']


@admin.register(BranchPoint)
class BranchPointAdmin(admin.ModelAdmin):
    list_display = ['chapter', 'prompt', 'voting_open', 'voting_ends', 'created_at']
    list_filter  = ['voting_open']
    inlines      = [BranchChoiceInline]
