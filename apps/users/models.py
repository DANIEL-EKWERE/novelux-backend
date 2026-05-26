# # # from django.contrib.auth.models import AbstractUser
# # # from django.db import models
# # # from config import settings

# # # class User(AbstractUser):
# # #     ROLE_READER = 'reader'
# # #     ROLE_AUTHOR = 'author'
# # #     ROLE_ADMIN  = 'admin'
# # #     ROLE_AE  = 'ae'  # Added AE role for Admin-Editor
# # #     ROLE_SE  = 'se'  # Added SE role for Site-Editor
# # #     ROLE_CHOICES = [
# # #         (ROLE_READER, 'Reader'),
# # #         (ROLE_AUTHOR, 'Author'),
# # #         (ROLE_ADMIN,  'Admin'),
# # #         (ROLE_AE,  'Admin-Editor'),
# # #         (ROLE_SE,  'Site-Editor'),
# # #     ]

# # #     email       = models.EmailField(unique=True)
# # #     role        = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_READER)
# # #     avatar      = models.ImageField(upload_to='avatars/', blank=True, null=True)
# # #     bio         = models.TextField(blank=True)
# # #     coin_balance= models.PositiveIntegerField(default=0)
# # #     is_vip      = models.BooleanField(default=False)
# # #     vip_expires = models.DateTimeField(blank=True, null=True)
# # #     total_tips_received = models.PositiveIntegerField(default=0)

# # #     # Reading stats
# # #     total_chapters_read = models.PositiveIntegerField(default=0)
# # #     reading_xp          = models.PositiveIntegerField(default=0)
# # #     reading_level       = models.PositiveIntegerField(default=1)

# # #     # Preferences
# # #     preferred_genres    = models.JSONField(default=list, blank=True)
# # #     preferred_language  = models.CharField(max_length=10, default='en')
# # #     night_mode          = models.BooleanField(default=False)
# # #     font_size           = models.PositiveSmallIntegerField(default=16)

# # #     created_at  = models.DateTimeField(auto_now_add=True)
# # #     updated_at  = models.DateTimeField(auto_now=True)

# # #     USERNAME_FIELD  = 'email'
# # #     REQUIRED_FIELDS = ['username']

# # #     class Meta:
# # #         db_table = 'users'

# # #     def __str__(self):
# # #         return f'{self.username} ({self.role})'

# # #     @property
# # #     def is_author(self):
# # #         return self.role == self.ROLE_AUTHOR

# # #     def add_coins(self, amount: int, reason: str = ''):
# # #         self.coin_balance += amount
# # #         self.save(update_fields=['coin_balance'])
# # #         CoinTransaction.objects.create(
# # #             user=self, amount=amount, transaction_type='credit', reason=reason
# # #         )

# # #     def deduct_coins(self, amount: int, reason: str = '') -> bool:
# # #         if self.coin_balance < amount:
# # #             return False
# # #         self.coin_balance -= amount
# # #         self.save(update_fields=['coin_balance'])
# # #         CoinTransaction.objects.create(
# # #             user=self, amount=amount, transaction_type='debit', reason=reason
# # #         )
# # #         return True

# # #     def add_reading_xp(self, xp: int):
# # #         self.reading_xp += xp
# # #         self.reading_level = (self.reading_xp // 500) + 1
# # #         self.save(update_fields=['reading_xp', 'reading_level'])


# # # class Follow(models.Model):
# # #     follower  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
# # #     following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
# # #     created_at= models.DateTimeField(auto_now_add=True)

# # #     class Meta:
# # #         db_table = 'follows'
# # #         unique_together = ('follower', 'following')

# # #     def __str__(self):
# # #         return f'{self.follower} → {self.following}'


# # # class CoinTransaction(models.Model):
# # #     TYPE_CREDIT = 'credit'
# # #     TYPE_DEBIT  = 'debit'
# # #     TYPE_CHOICES = [(TYPE_CREDIT, 'Credit'), (TYPE_DEBIT, 'Debit')]

# # #     user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coin_transactions')
# # #     amount           = models.PositiveIntegerField()
# # #     transaction_type = models.CharField(max_length=6, choices=TYPE_CHOICES)
# # #     reason           = models.CharField(max_length=255, blank=True)
# # #     balance_after    = models.PositiveIntegerField(default=0)
# # #     created_at       = models.DateTimeField(auto_now_add=True)

# # #     class Meta:
# # #         db_table = 'coin_transactions'
# # #         ordering = ['-created_at']


# # # class UserPreferences(models.Model):
# # #     GENDER_CHOICES = [
# # #         ('male',             'Male'),
# # #         ('female',           'Female'),
# # #         ('prefer_not_to_say','Prefer not to say'),
# # #     ]
# # #     user             = models.OneToOneField(
# # #                            settings.AUTH_USER_MODEL,
# # #                            on_delete=models.CASCADE,
# # #                            related_name='preferences')
# # #     preferred_genres = models.JSONField(default=list)
# # #     gender           = models.CharField(max_length=30, choices=GENDER_CHOICES,
# # #                            blank=True, default='')
# # #     updated_at       = models.DateTimeField(auto_now=True)
 
# # #     def __str__(self):
# # #         return f'{self.user.username} — preferences'


# # # class AuthorProfile(models.Model):
# # #     user               = models.OneToOneField(User, on_delete=models.CASCADE, related_name='author_profile')
# # #     pen_name           = models.CharField(max_length=100, blank=True)
# # #     total_earnings     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
# # #     pending_payout     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
# # #     contract_type      = models.CharField(max_length=20, choices=[('exclusive','Exclusive'),('non_exclusive','Non-Exclusive')], default='non_exclusive')
# # #     is_verified        = models.BooleanField(default=False)
# # #     payout_method      = models.CharField(max_length=50, blank=True)
# # #     payout_details     = models.JSONField(default=dict, blank=True)
# # #     joined_as_author   = models.DateTimeField(auto_now_add=True)

# # #     class Meta:
# # #         db_table = 'author_profiles'

# # #     def __str__(self):
# # #         return f'Author: {self.user.username}'
    
# # # class FCMDevice(models.Model):
# # #     user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens',
# # #                        null=True, blank=True)
# # #     token       = models.CharField(max_length=255, unique=True)
# # #     platform    = models.CharField(max_length=225)
# # #     device_model    = models.CharField(max_length=225)
# # #     app_version    = models.CharField(max_length=225)
# # #     is_active    = models.BooleanField(default=True)
# # #     created_at   = models.DateTimeField(auto_now_add=True)
# # #     updated_at   = models.DateTimeField(auto_now=True)
 
# # #     class Meta:
# # #         db_table = 'fcm_tokens'
# # #         ordering = ['-updated_at']
 
# # #     def __str__(self):
# # #         return f'{self.user} — {self.platform} — {self.token[:20]}...'

# # #     # class Meta:
# # #         # db_table = 'fcm_tokens'

# # #     # def __str__(self):
# # #     #     return f'FCM Token for {self.user.first_name}'

# # import secrets
# # from django.contrib.auth.models import AbstractUser
# # from django.db import models
# # from config import settings

# # class User(AbstractUser):
# #     ROLE_READER = 'reader'
# #     ROLE_AUTHOR = 'author'
# #     ROLE_ADMIN  = 'admin'
# #     ROLE_AE     = 'ae'   # Assistant Editor
# #     ROLE_SE     = 'se'   # Senior Editor
# #     ROLE_CE     = 'ce'   # Chief Editor — oversees all editors
# #     ROLE_CHOICES = [
# #         (ROLE_READER, 'Reader'),
# #         (ROLE_AUTHOR, 'Author'),
# #         (ROLE_ADMIN,  'Admin'),
# #         (ROLE_AE,     'Assistant Editor'),
# #         (ROLE_SE,     'Senior Editor'),
# #         (ROLE_CE,     'Chief Editor'),
# #     ]

# #     email       = models.EmailField(unique=True)
# #     role        = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_READER)
# #     avatar      = models.ImageField(upload_to='avatars/', blank=True, null=True)
# #     bio         = models.TextField(blank=True)
# #     coin_balance= models.PositiveIntegerField(default=0)
# #     is_vip      = models.BooleanField(default=False)
# #     vip_expires = models.DateTimeField(blank=True, null=True)
# #     total_tips_received = models.PositiveIntegerField(default=0)

# #     # Editor invite code — generated once when an AE account is created.
# #     # Authors enter this code at signup or in profile settings to link themselves.
# #     editor_code = models.CharField(
# #         max_length=12, unique=True, blank=True, null=True,
# #         help_text='Unique invite code for AEs to share with authors.',
# #         db_index=True,
# #     )

# #     # Reading stats
# #     total_chapters_read = models.PositiveIntegerField(default=0)
# #     reading_xp          = models.PositiveIntegerField(default=0)
# #     reading_level       = models.PositiveIntegerField(default=1)

# #     # Preferences
# #     preferred_genres    = models.JSONField(default=list, blank=True)
# #     preferred_language  = models.CharField(max_length=10, default='en')
# #     night_mode          = models.BooleanField(default=False)
# #     font_size           = models.PositiveSmallIntegerField(default=16)

# #     created_at  = models.DateTimeField(auto_now_add=True)
# #     updated_at  = models.DateTimeField(auto_now=True)

# #     USERNAME_FIELD  = 'email'
# #     REQUIRED_FIELDS = ['username']

# #     class Meta:
# #         db_table = 'users'

# #     def __str__(self):
# #         return f'{self.username} ({self.role})'

# #     @property
# #     def is_author(self):
# #         return self.role == self.ROLE_AUTHOR

# #     def add_coins(self, amount: int, reason: str = ''):
# #         self.coin_balance += amount
# #         self.save(update_fields=['coin_balance'])
# #         CoinTransaction.objects.create(
# #             user=self, amount=amount, transaction_type='credit', reason=reason
# #         )

# #     def deduct_coins(self, amount: int, reason: str = '') -> bool:
# #         if self.coin_balance < amount:
# #             return False
# #         self.coin_balance -= amount
# #         self.save(update_fields=['coin_balance'])
# #         CoinTransaction.objects.create(
# #             user=self, amount=amount, transaction_type='debit', reason=reason
# #         )
# #         return True

# #     def add_reading_xp(self, xp: int):
# #         self.reading_xp += xp
# #         self.reading_level = (self.reading_xp // 500) + 1
# #         self.save(update_fields=['reading_xp', 'reading_level'])

# #     def generate_editor_code(self):
# #         """Generate a unique 8-char alphanumeric editor code for AE accounts."""
# #         if self.role != self.ROLE_AE:
# #             return None
# #         if self.editor_code:
# #             return self.editor_code
# #         while True:
# #             code = secrets.token_urlsafe(6).upper()[:8]
# #             if not User.objects.filter(editor_code=code).exists():
# #                 self.editor_code = code
# #                 self.save(update_fields=['editor_code'])
# #                 return code


# # class Follow(models.Model):
# #     follower  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
# #     following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
# #     created_at= models.DateTimeField(auto_now_add=True)

# #     class Meta:
# #         db_table = 'follows'
# #         unique_together = ('follower', 'following')

# #     def __str__(self):
# #         return f'{self.follower} → {self.following}'


# # class CoinTransaction(models.Model):
# #     TYPE_CREDIT = 'credit'
# #     TYPE_DEBIT  = 'debit'
# #     TYPE_CHOICES = [(TYPE_CREDIT, 'Credit'), (TYPE_DEBIT, 'Debit')]

# #     user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coin_transactions')
# #     amount           = models.PositiveIntegerField()
# #     transaction_type = models.CharField(max_length=6, choices=TYPE_CHOICES)
# #     reason           = models.CharField(max_length=255, blank=True)
# #     balance_after    = models.PositiveIntegerField(default=0)
# #     created_at       = models.DateTimeField(auto_now_add=True)

# #     class Meta:
# #         db_table = 'coin_transactions'
# #         ordering = ['-created_at']

# # class UserPreferences(models.Model):
# #     GENDER_CHOICES = [
# #         ('male',             'Male'),
# #         ('female',           'Female'),
# #         ('prefer_not_to_say','Prefer not to say'),
# #     ]
# #     user             = models.OneToOneField(
# #                            settings.AUTH_USER_MODEL,
# #                            on_delete=models.CASCADE,
# #                            related_name='preferences')
# #     preferred_genres = models.JSONField(default=list)
# #     gender           = models.CharField(max_length=30, choices=GENDER_CHOICES,
# #                            blank=True, default='')
# #     updated_at       = models.DateTimeField(auto_now=True)
 
# #     def __str__(self):
# #         return f'{self.user.username} — preferences'


# # class AuthorProfile(models.Model):
# #     user               = models.OneToOneField(User, on_delete=models.CASCADE, related_name='author_profile')
# #     pen_name           = models.CharField(max_length=100, blank=True)
# #     total_earnings     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
# #     pending_payout     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
# #     contract_type      = models.CharField(max_length=20, choices=[('exclusive','Exclusive'),('non_exclusive','Non-Exclusive')], default='non_exclusive')
# #     is_verified        = models.BooleanField(default=False)
# #     payout_method      = models.CharField(max_length=50, blank=True)
# #     payout_details     = models.JSONField(default=dict, blank=True)
# #     joined_as_author   = models.DateTimeField(auto_now_add=True)

# #     class Meta:
# #         db_table = 'author_profiles'

# #     def __str__(self):
# #         return f'Author: {self.user.username}'
    
# # class FCMDevice(models.Model):
# #     user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens',
# #                        null=True, blank=True)
# #     token       = models.CharField(max_length=255, unique=True)
# #     platform    = models.CharField(max_length=225)
# #     device_model    = models.CharField(max_length=225)
# #     app_version    = models.CharField(max_length=225)
# #     is_active    = models.BooleanField(default=True)
# #     created_at   = models.DateTimeField(auto_now_add=True)
# #     updated_at   = models.DateTimeField(auto_now=True)
 
# #     class Meta:
# #         db_table = 'fcm_tokens'
# #         ordering = ['-updated_at']
 
# #     def __str__(self):
# #         return f'{self.user} — {self.platform} — {self.token[:20]}...'

# #     # class Meta:
# #         # db_table = 'fcm_tokens'

# #     # def __str__(self):
# #     #     return f'FCM Token for {self.user.first_name}'

# import secrets
# from django.contrib.auth.models import AbstractUser
# from django.db import models
# from config import settings

# class User(AbstractUser):
#     ROLE_READER = 'reader'
#     ROLE_AUTHOR = 'author'
#     ROLE_ADMIN  = 'admin'
#     ROLE_AE     = 'ae'   # Assistant Editor
#     ROLE_SE     = 'se'   # Senior Editor
#     ROLE_CE     = 'ce'   # Chief Editor — oversees all editors
#     ROLE_CHOICES = [
#         (ROLE_READER, 'Reader'),
#         (ROLE_AUTHOR, 'Author'),
#         (ROLE_ADMIN,  'Admin'),
#         (ROLE_AE,     'Assistant Editor'),
#         (ROLE_SE,     'Senior Editor'),
#         (ROLE_CE,     'Chief Editor'),
#     ]

#     email       = models.EmailField(unique=True)
#     role        = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_READER)
#     avatar      = models.ImageField(upload_to='avatars/', blank=True, null=True)
#     bio         = models.TextField(blank=True)
#     coin_balance= models.PositiveIntegerField(default=0)
#     is_vip      = models.BooleanField(default=False)
#     vip_expires = models.DateTimeField(blank=True, null=True)
#     total_tips_received = models.PositiveIntegerField(default=0)

#     # Editor invite code — generated once when an AE account is created.
#     # Authors enter this code at signup or in profile settings to link themselves.
#     editor_code = models.CharField(
#         max_length=12, unique=True, blank=True, null=True,
#         help_text='Unique invite code for AEs to share with authors.',
#         db_index=True,
#     )

#     # Reading stats
#     total_chapters_read = models.PositiveIntegerField(default=0)
#     reading_xp          = models.PositiveIntegerField(default=0)
#     reading_level       = models.PositiveIntegerField(default=1)

#     # Preferences
#     preferred_genres    = models.JSONField(default=list, blank=True)
#     preferred_language  = models.CharField(max_length=10, default='en')
#     night_mode          = models.BooleanField(default=False)
#     font_size           = models.PositiveSmallIntegerField(default=16)

#     created_at  = models.DateTimeField(auto_now_add=True)
#     updated_at  = models.DateTimeField(auto_now=True)

#     USERNAME_FIELD  = 'email'
#     REQUIRED_FIELDS = ['username']

#     class Meta:
#         db_table = 'users'

#     def __str__(self):
#         return f'{self.username} ({self.role})'

#     @property
#     def is_author(self):
#         return self.role == self.ROLE_AUTHOR

#     def add_coins(self, amount: int, reason: str = ''):
#         self.coin_balance += amount
#         self.save(update_fields=['coin_balance'])
#         CoinTransaction.objects.create(
#             user=self, amount=amount, transaction_type='credit', reason=reason
#         )

#     def deduct_coins(self, amount: int, reason: str = '') -> bool:
#         if self.coin_balance < amount:
#             return False
#         self.coin_balance -= amount
#         self.save(update_fields=['coin_balance'])
#         CoinTransaction.objects.create(
#             user=self, amount=amount, transaction_type='debit', reason=reason
#         )
#         return True

#     def add_reading_xp(self, xp: int):
#         self.reading_xp += xp
#         self.reading_level = (self.reading_xp // 500) + 1
#         self.save(update_fields=['reading_xp', 'reading_level'])

#     def generate_editor_code(self):
#         """Generate a unique 8-char alphanumeric editor code for AE accounts."""
#         if self.role != self.ROLE_AE:
#             return None
#         if self.editor_code:
#             return self.editor_code
#         while True:
#             code = secrets.token_urlsafe(6).upper()[:8]
#             if not User.objects.filter(editor_code=code).exists():
#                 self.editor_code = code
#                 self.save(update_fields=['editor_code'])
#                 return code


# class Follow(models.Model):
#     follower  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
#     following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
#     created_at= models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'follows'
#         unique_together = ('follower', 'following')

#     def __str__(self):
#         return f'{self.follower} → {self.following}'


# class CoinTransaction(models.Model):
#     TYPE_CREDIT = 'credit'
#     TYPE_DEBIT  = 'debit'
#     TYPE_CHOICES = [(TYPE_CREDIT, 'Credit'), (TYPE_DEBIT, 'Debit')]

#     user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coin_transactions')
#     amount           = models.PositiveIntegerField()
#     transaction_type = models.CharField(max_length=6, choices=TYPE_CHOICES)
#     reason           = models.CharField(max_length=255, blank=True)
#     balance_after    = models.PositiveIntegerField(default=0)
#     created_at       = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'coin_transactions'
#         ordering = ['-created_at']

# # class UserPreferences(models.Model):
# #     GENDER_CHOICES = [
# #         ('male',             'Male'),
# #         ('female',           'Female'),
# #         ('prefer_not_to_say','Prefer not to say'),
# #     ]
# #     user              = models.OneToOneField(
# #                             settings.AUTH_USER_MODEL,
# #                             on_delete=models.CASCADE,
# #                             related_name='preferences')
# #     preferred_genres  = models.JSONField(default=list)
# #     gender            = models.CharField(
# #                             max_length=30, choices=GENDER_CHOICES,
# #                             blank=True, default='')
# #     updated_at        = models.DateTimeField(auto_now=True)
 
# #     def __str__(self):
# #         return f'{self.user.username} preferences'

# class UserPreferences(models.Model):
#     GENDER_CHOICES = [
#         ('male',             'Male'),
#         ('female',           'Female'),
#         ('prefer_not_to_say','Prefer not to say'),
#     ]
#     user             = models.OneToOneField(
#                            settings.AUTH_USER_MODEL,
#                            on_delete=models.CASCADE,
#                            related_name='preferences')
#     preferred_genres = models.JSONField(default=list)
#     gender           = models.CharField(max_length=30, choices=GENDER_CHOICES,
#                            blank=True, default='')
#     updated_at       = models.DateTimeField(auto_now=True)
 
#     def __str__(self):
#         return f'{self.user.username} — preferences'


# class AuthorProfile(models.Model):
#     user               = models.OneToOneField(User, on_delete=models.CASCADE, related_name='author_profile')
#     pen_name           = models.CharField(max_length=100, blank=True)
#     total_earnings     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
#     pending_payout     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
#     contract_type      = models.CharField(max_length=20, choices=[('exclusive','Exclusive'),('non_exclusive','Non-Exclusive')], default='non_exclusive')
#     is_verified        = models.BooleanField(default=False)
#     payout_method      = models.CharField(max_length=50, blank=True)
#     payout_details     = models.JSONField(default=dict, blank=True)
#     joined_as_author   = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'author_profiles'

#     def __str__(self):
#         return f'Author: {self.user.username}'
    
# class FCMDevice(models.Model):
#     user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens',
#                        null=True, blank=True)
#     token       = models.CharField(max_length=255, unique=True)
#     platform    = models.CharField(max_length=225)
#     device_model    = models.CharField(max_length=225)
#     app_version    = models.CharField(max_length=225)
#     is_active    = models.BooleanField(default=True)
#     created_at   = models.DateTimeField(auto_now_add=True)
#     updated_at   = models.DateTimeField(auto_now=True)
 
#     class Meta:
#         db_table = 'fcm_tokens'
#         ordering = ['-updated_at']
 
#     def __str__(self):
#         return f'{self.user} — {self.platform} — {self.token[:20]}...'

#     # class Meta:
#         # db_table = 'fcm_tokens'

#     # def __str__(self):
#     #     return f'FCM Token for {self.user.first_name}'


# import secrets
# from django.contrib.auth.models import AbstractUser
# from django.db import models
# from config import settings

# class User(AbstractUser):
#     ROLE_READER = 'reader'
#     ROLE_AUTHOR = 'author'
#     ROLE_ADMIN  = 'admin'
#     ROLE_AE     = 'ae'   # Acquisition Editor — talent scout, recruits authors
#     ROLE_SE     = 'se'   # Senior Editor — reviews chapters, quality control
#     ROLE_CE     = 'ce'   # Chief Editor — head of editorial, sends contracts
#     ROLE_CHOICES = [
#         (ROLE_READER, 'Reader'),
#         (ROLE_AUTHOR, 'Author'),
#         (ROLE_ADMIN,  'Admin'),
#         (ROLE_AE,     'Acquisition Editor'),
#         (ROLE_SE,     'Senior Editor'),
#         (ROLE_CE,     'Chief Editor'),
#     ]

#     email       = models.EmailField(unique=True)
#     role        = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_READER)
#     avatar      = models.ImageField(upload_to='avatars/', blank=True, null=True)
#     bio         = models.TextField(blank=True)
#     coin_balance= models.PositiveIntegerField(default=0)
#     is_vip      = models.BooleanField(default=False)
#     vip_expires = models.DateTimeField(blank=True, null=True)
#     total_tips_received = models.PositiveIntegerField(default=0)

#     # Editor invite code — generated for AE and SE accounts.
#     # Authors enter this code to link themselves to an editor.
#     editor_code = models.CharField(
#         max_length=12, unique=True, blank=True, null=True,
#         help_text='Unique invite code for AEs/SEs to share with authors.',
#         db_index=True,
#     )

#     # Reading stats
#     total_chapters_read = models.PositiveIntegerField(default=0)
#     reading_xp          = models.PositiveIntegerField(default=0)
#     reading_level       = models.PositiveIntegerField(default=1)

#     # Preferences
#     preferred_genres    = models.JSONField(default=list, blank=True)
#     preferred_language  = models.CharField(max_length=10, default='en')
#     night_mode          = models.BooleanField(default=False)
#     font_size           = models.PositiveSmallIntegerField(default=16)

#     created_at  = models.DateTimeField(auto_now_add=True)
#     updated_at  = models.DateTimeField(auto_now=True)

#     USERNAME_FIELD  = 'email'
#     REQUIRED_FIELDS = ['username']

#     class Meta:
#         db_table = 'users'

#     def __str__(self):
#         return f'{self.username} ({self.role})'

#     @property
#     def is_author(self):
#         return self.role == self.ROLE_AUTHOR

#     def add_coins(self, amount: int, reason: str = ''):
#         self.coin_balance += amount
#         self.save(update_fields=['coin_balance'])
#         CoinTransaction.objects.create(
#             user=self, amount=amount, transaction_type='credit', reason=reason
#         )

#     def deduct_coins(self, amount: int, reason: str = '') -> bool:
#         if self.coin_balance < amount:
#             return False
#         self.coin_balance -= amount
#         self.save(update_fields=['coin_balance'])
#         CoinTransaction.objects.create(
#             user=self, amount=amount, transaction_type='debit', reason=reason
#         )
#         return True

#     def add_reading_xp(self, xp: int):
#         self.reading_xp += xp
#         self.reading_level = (self.reading_xp // 500) + 1
#         self.save(update_fields=['reading_xp', 'reading_level'])

#     def generate_editor_code(self):
#         """Generate a unique 8-char alphanumeric editor code for AE and SE accounts."""
#         if self.role not in (self.ROLE_AE, self.ROLE_SE):
#             return None
#         if self.editor_code:
#             return self.editor_code
#         while True:
#             code = secrets.token_urlsafe(6).upper()[:8]
#             if not User.objects.filter(editor_code=code).exists():
#                 self.editor_code = code
#                 self.save(update_fields=['editor_code'])
#                 return code


# class Follow(models.Model):
#     follower  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
#     following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
#     created_at= models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'follows'
#         unique_together = ('follower', 'following')

#     def __str__(self):
#         return f'{self.follower} → {self.following}'


# class CoinTransaction(models.Model):
#     TYPE_CREDIT = 'credit'
#     TYPE_DEBIT  = 'debit'
#     TYPE_CHOICES = [(TYPE_CREDIT, 'Credit'), (TYPE_DEBIT, 'Debit')]

#     user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coin_transactions')
#     amount           = models.PositiveIntegerField()
#     transaction_type = models.CharField(max_length=6, choices=TYPE_CHOICES)
#     reason           = models.CharField(max_length=255, blank=True)
#     balance_after    = models.PositiveIntegerField(default=0)
#     created_at       = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'coin_transactions'
#         ordering = ['-created_at']

# # class UserPreferences(models.Model):
# #     GENDER_CHOICES = [
# #         ('male',             'Male'),
# #         ('female',           'Female'),
# #         ('prefer_not_to_say','Prefer not to say'),
# #     ]
# #     user              = models.OneToOneField(
# #                             settings.AUTH_USER_MODEL,
# #                             on_delete=models.CASCADE,
# #                             related_name='preferences')
# #     preferred_genres  = models.JSONField(default=list)
# #     gender            = models.CharField(
# #                             max_length=30, choices=GENDER_CHOICES,
# #                             blank=True, default='')
# #     updated_at        = models.DateTimeField(auto_now=True)
 
# #     def __str__(self):
# #         return f'{self.user.username} preferences'

# class UserPreferences(models.Model):
#     GENDER_CHOICES = [
#         ('male',             'Male'),
#         ('female',           'Female'),
#         ('prefer_not_to_say','Prefer not to say'),
#     ]
#     user             = models.OneToOneField(
#                            settings.AUTH_USER_MODEL,
#                            on_delete=models.CASCADE,
#                            related_name='preferences')
#     preferred_genres = models.JSONField(default=list)
#     gender           = models.CharField(max_length=30, choices=GENDER_CHOICES,
#                            blank=True, default='')
#     updated_at       = models.DateTimeField(auto_now=True)
 
#     def __str__(self):
#         return f'{self.user.username} — preferences'


# class AuthorProfile(models.Model):
#     user               = models.OneToOneField(User, on_delete=models.CASCADE, related_name='author_profile')
#     pen_name           = models.CharField(max_length=100, blank=True)
#     total_earnings     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
#     pending_payout     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
#     contract_type      = models.CharField(max_length=20, choices=[('exclusive','Exclusive'),('non_exclusive','Non-Exclusive')], default='non_exclusive')
#     has_contract       = models.BooleanField(
#         default=False,
#         help_text='True once the author has signed a contract with the platform. '
#                   'Chapters bypass SE review and are published immediately.',
#     )
#     contract_signed_at = models.DateTimeField(
#         null=True, blank=True,
#         help_text='Timestamp of when the author accepted the contract.',
#     )
#     is_verified        = models.BooleanField(default=False)
#     payout_method      = models.CharField(max_length=50, blank=True)
#     payout_details     = models.JSONField(default=dict, blank=True)
#     joined_as_author   = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'author_profiles'

#     def __str__(self):
#         return f'Author: {self.user.username}'
    
# class FCMDevice(models.Model):
#     user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens',
#                        null=True, blank=True)
#     token       = models.CharField(max_length=255, unique=True)
#     platform    = models.CharField(max_length=225)
#     device_model    = models.CharField(max_length=225)
#     app_version    = models.CharField(max_length=225)
#     is_active    = models.BooleanField(default=True)
#     created_at   = models.DateTimeField(auto_now_add=True)
#     updated_at   = models.DateTimeField(auto_now=True)
 
#     class Meta:
#         db_table = 'fcm_tokens'
#         ordering = ['-updated_at']
 
#     def __str__(self):
#         return f'{self.user} — {self.platform} — {self.token[:20]}...'

#     # class Meta:
#         # db_table = 'fcm_tokens'

#     # def __str__(self):
#     #     return f'FCM Token for {self.user.first_name}'


import secrets
from django.contrib.auth.models import AbstractUser
from django.db import models
from config import settings

class User(AbstractUser):
    ROLE_READER = 'reader'
    ROLE_AUTHOR = 'author'
    ROLE_ADMIN  = 'admin'
    ROLE_SE     = 'se'   # Senior Editor — reviews chapters, quality control
    ROLE_CE     = 'ce'   # Chief Editor — head of editorial, sends contracts
    ROLE_CHOICES = [
        (ROLE_READER, 'Reader'),
        (ROLE_AUTHOR, 'Author'),
        (ROLE_ADMIN,  'Admin'),
        (ROLE_SE,     'Senior Editor'),
        (ROLE_CE,     'Chief Editor'),
    ]

    email       = models.EmailField(unique=True)
    role        = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_READER)
    avatar      = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio         = models.TextField(blank=True)
    coin_balance= models.PositiveIntegerField(default=0)
    is_vip      = models.BooleanField(default=False)
    vip_expires = models.DateTimeField(blank=True, null=True)
    total_tips_received = models.PositiveIntegerField(default=0)

    # Editor invite code — generated for AE and SE accounts.
    # Authors enter this code to link themselves to an editor.
    editor_code = models.CharField(
        max_length=12, unique=True, blank=True, null=True,
        help_text='Unique invite code for SEs to share with authors.',
        db_index=True,
    )

    # Reading stats
    total_chapters_read = models.PositiveIntegerField(default=0)
    reading_xp          = models.PositiveIntegerField(default=0)
    reading_level       = models.PositiveIntegerField(default=1)

    # Preferences
    preferred_genres    = models.JSONField(default=list, blank=True)
    preferred_language  = models.CharField(max_length=10, default='en')
    night_mode          = models.BooleanField(default=False)
    font_size           = models.PositiveSmallIntegerField(default=16)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f'{self.username} ({self.role})'

    @property
    def is_author(self):
        return self.role == self.ROLE_AUTHOR

    def add_coins(self, amount: int, reason: str = ''):
        self.coin_balance += amount
        self.save(update_fields=['coin_balance'])
        CoinTransaction.objects.create(
            user=self, amount=amount, transaction_type='credit', reason=reason
        )

    def deduct_coins(self, amount: int, reason: str = '') -> bool:
        if self.coin_balance < amount:
            return False
        self.coin_balance -= amount
        self.save(update_fields=['coin_balance'])
        CoinTransaction.objects.create(
            user=self, amount=amount, transaction_type='debit', reason=reason
        )
        return True

    def add_reading_xp(self, xp: int):
        self.reading_xp += xp
        self.reading_level = (self.reading_xp // 500) + 1
        self.save(update_fields=['reading_xp', 'reading_level'])

    def generate_editor_code(self):
        """Generate a unique 8-char alphanumeric editor code for SE accounts."""
        if self.role != self.ROLE_SE:
            return None
        if self.editor_code:
            return self.editor_code
        while True:
            code = secrets.token_urlsafe(6).upper()[:8]
            if not User.objects.filter(editor_code=code).exists():
                self.editor_code = code
                self.save(update_fields=['editor_code'])
                return code


class Follow(models.Model):
    follower  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'follows'
        unique_together = ('follower', 'following')

    def __str__(self):
        return f'{self.follower} → {self.following}'


class CoinTransaction(models.Model):
    TYPE_CREDIT = 'credit'
    TYPE_DEBIT  = 'debit'
    TYPE_CHOICES = [(TYPE_CREDIT, 'Credit'), (TYPE_DEBIT, 'Debit')]

    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coin_transactions')
    amount           = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=6, choices=TYPE_CHOICES)
    reason           = models.CharField(max_length=255, blank=True)
    balance_after    = models.PositiveIntegerField(default=0)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coin_transactions'
        ordering = ['-created_at']

# class UserPreferences(models.Model):
#     GENDER_CHOICES = [
#         ('male',             'Male'),
#         ('female',           'Female'),
#         ('prefer_not_to_say','Prefer not to say'),
#     ]
#     user              = models.OneToOneField(
#                             settings.AUTH_USER_MODEL,
#                             on_delete=models.CASCADE,
#                             related_name='preferences')
#     preferred_genres  = models.JSONField(default=list)
#     gender            = models.CharField(
#                             max_length=30, choices=GENDER_CHOICES,
#                             blank=True, default='')
#     updated_at        = models.DateTimeField(auto_now=True)
 
#     def __str__(self):
#         return f'{self.user.username} preferences'

class UserPreferences(models.Model):
    GENDER_CHOICES = [
        ('male',             'Male'),
        ('female',           'Female'),
        ('prefer_not_to_say','Prefer not to say'),
    ]
    user             = models.OneToOneField(
                           settings.AUTH_USER_MODEL,
                           on_delete=models.CASCADE,
                           related_name='preferences')
    preferred_genres = models.JSONField(default=list)
    gender           = models.CharField(max_length=30, choices=GENDER_CHOICES,
                           blank=True, default='')
    updated_at       = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return f'{self.user.username} — preferences'


class AuthorProfile(models.Model):
    user               = models.OneToOneField(User, on_delete=models.CASCADE, related_name='author_profile')
    pen_name           = models.CharField(max_length=100, blank=True)
    total_earnings     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_payout     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    contract_type      = models.CharField(max_length=20, choices=[('exclusive','Exclusive'),('non_exclusive','Non-Exclusive')], default='non_exclusive')
    has_contract       = models.BooleanField(
        default=False,
        help_text='True once the author has signed a contract with the platform. '
                  'Chapters bypass SE review and are published immediately.',
    )
    contract_signed_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Timestamp of when the author accepted the contract.',
    )
    is_verified        = models.BooleanField(default=False)
    payout_method      = models.CharField(max_length=50, blank=True)
    payout_details     = models.JSONField(default=dict, blank=True)
    joined_as_author   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'author_profiles'

    def __str__(self):
        return f'Author: {self.user.username}'


class AuthorKYC(models.Model):
    ID_NATIONAL  = 'national_id'
    ID_PASSPORT  = 'passport'
    ID_DRIVERS   = 'drivers_license'
    ID_CHOICES   = [
        (ID_NATIONAL, 'National ID Card'),
        (ID_PASSPORT, 'Passport'),
        (ID_DRIVERS,  "Driver's License"),
    ]

    PAY_BANK   = 'bank_account'
    PAY_PAYPAL = 'paypal'
    PAY_CHOICES = [
        (PAY_BANK,   'Bank Account'),
        (PAY_PAYPAL, 'PayPal'),
    ]

    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES  = [
        (STATUS_PENDING,  'Pending Review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='kyc')
    # ── Personal ─────────────────────────────────────────────────────────
    full_name        = models.CharField(max_length=150, help_text='Real name as on your ID document')
    phone            = models.CharField(max_length=30)
    contact_address  = models.CharField(max_length=255)
    country          = models.CharField(max_length=100)
    id_type          = models.CharField(max_length=20, choices=ID_CHOICES, default=ID_NATIONAL)
    id_number        = models.CharField(max_length=60)
    id_document      = models.ImageField(upload_to='kyc/id_docs/', help_text='Photo of government-issued ID')
    # ── Payment ──────────────────────────────────────────────────────────
    payment_method   = models.CharField(max_length=20, choices=PAY_CHOICES, default=PAY_BANK)
    account_holder   = models.CharField(max_length=150, blank=True)
    bank_name        = models.CharField(max_length=150, blank=True)
    account_number   = models.CharField(max_length=60,  blank=True)
    swift_code       = models.CharField(max_length=11,  blank=True)
    bank_country     = models.CharField(max_length=100, blank=True)
    paypal_email     = models.EmailField(blank=True)
    # ── Status ───────────────────────────────────────────────────────────
    status           = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_notes      = models.TextField(blank=True)
    submitted_at     = models.DateTimeField(auto_now_add=True)
    reviewed_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'author_kyc'

    def __str__(self):
        return f'KYC: {self.user.username} [{self.status}]'


class FCMDevice(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens',
                       null=True, blank=True)
    token       = models.CharField(max_length=255, unique=True)
    platform    = models.CharField(max_length=225)
    device_model    = models.CharField(max_length=225)
    app_version    = models.CharField(max_length=225)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
 
    class Meta:
        db_table = 'fcm_tokens'
        ordering = ['-updated_at']
 
    def __str__(self):
        return f'{self.user} — {self.platform} — {self.token[:20]}...'

    # class Meta:
        # db_table = 'fcm_tokens'

    # def __str__(self):
    #     return f'FCM Token for {self.user.first_name}'