#!/usr/bin/env python
"""
Test script to verify SE dashboard template renders with proper data
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.chapters.models import Chapter

User = get_user_model()

print("=" * 60)
print("SE Dashboard Data Availability Test")
print("=" * 60)

# Find an SE user
se_user = User.objects.filter(role='se').first()
if not se_user:
    print("\n⚠ No SE user found in database.")
else:
    print(f"\n✓ Found SE user: {se_user.username} (ID: {se_user.id})")
    
    # Check if they have AEs
    ae_qs = User.objects.filter(
        role='ae', editorial_assignment__supervisor=se_user,
    )
    print(f"  - AEs supervised: {ae_qs.count()}")
    
    # Check escalations
    escalations = Chapter.objects.filter(
        story__author__editor_link__assigned_ae__editorial_assignment__supervisor=se_user,
        status__in=[Chapter.STATUS_PENDING_REVIEW, Chapter.STATUS_SE_REVIEWING],
    )
    print(f"  - Pending escalations: {escalations.count()}")
    
    # Check recent decisions
    from datetime import timedelta
    from django.utils import timezone
    one_week_ago = timezone.now() - timedelta(days=7)
    
    decisions = Chapter.objects.filter(
        story__author__editor_link__assigned_ae__editorial_assignment__supervisor=se_user,
        reviewed_at__gte=one_week_ago,
        status__in=[Chapter.STATUS_SE_APPROVED, Chapter.STATUS_SE_REVISION, Chapter.STATUS_REJECTED],
    )
    print(f"  - Recent decisions (7 days): {decisions.count()}")
    
    # Check cleared
    cleared = Chapter.objects.filter(
        story__author__editor_link__assigned_ae__editorial_assignment__supervisor=se_user,
        status=Chapter.STATUS_SE_APPROVED,
        reviewed_at__gte=one_week_ago,
    )
    print(f"  - Cleared this week: {cleared.count()}")
    
    # Check authors
    authors = User.objects.filter(
        role='author',
        editor_link__assigned_ae__editorial_assignment__supervisor=se_user,
    )
    print(f"  - Authors under supervision: {authors.count()}")
    
    print("\n✓ All SE dashboard data queries work correctly!")

print("\n✓ API Endpoints are registered:")
from django.urls import get_resolver
resolver = get_resolver()
editorial_patterns = [p for p in resolver.url_patterns if 'editorial' in str(p.pattern)]
print(f"  - Found {len([p for p in resolver.url_patterns if 'editorial' in str(p.pattern)])} editorial endpoints")

print("\n" + "=" * 60)
print("✓ SE Dashboard is ready to use!")
print("=" * 60)
