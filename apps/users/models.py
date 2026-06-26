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
    coin_balance  = models.PositiveIntegerField(default=0)
    bonus_balance = models.PositiveIntegerField(default=0,
                      help_text='Coins earned from rewards (checkin, ads, reading). Spent before paid coins.')
    is_vip        = models.BooleanField(default=False)
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

    registration_ip = models.GenericIPAddressField(null=True, blank=True)
    is_banned       = models.BooleanField(default=False)
    ban_reason      = models.TextField(blank=True)

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

    @property
    def total_balance(self):
        """Total spendable coins: paid + bonus."""
        return self.coin_balance + self.bonus_balance

    def add_coins(self, amount: int, reason: str = ''):
        """Add purchased coins (coin pack / subscription)."""
        self.coin_balance += amount
        self.save(update_fields=['coin_balance'])
        CoinTransaction.objects.create(
            user=self, amount=amount, transaction_type='credit', reason=reason
        )

    def add_bonus(self, amount: int, reason: str = ''):
        """Add reward coins (daily login, ads, reading milestones, etc.)."""
        self.bonus_balance += amount
        self.save(update_fields=['bonus_balance'])
        CoinTransaction.objects.create(
            user=self, amount=amount, transaction_type='bonus', reason=reason
        )

    def deduct_coins(self, amount: int, reason: str = '') -> bool:
        """Deduct coins for a purchase. Drains bonus balance first, then paid coins."""
        if self.total_balance < amount:
            return False
        remaining = amount
        if self.bonus_balance > 0:
            from_bonus = min(self.bonus_balance, remaining)
            self.bonus_balance -= from_bonus
            remaining -= from_bonus
        if remaining > 0:
            self.coin_balance -= remaining
        self.save(update_fields=['coin_balance', 'bonus_balance'])
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
    TYPE_BONUS  = 'bonus'
    TYPE_CHOICES = [
        (TYPE_CREDIT, 'Credit'),
        (TYPE_DEBIT,  'Debit'),
        (TYPE_BONUS,  'Bonus Reward'),
    ]

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
    completion_bonus   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
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

    # Balance visibility — approved by SE on the 6th of each month
    balance_approved_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When an SE last approved this balance for the current month.',
    )
    balance_approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_author_balances',
        limit_choices_to={'role': 'se'},
    )

    def balance_is_visible(self):
        """
        True if the balance has been SE-approved for the current month
        AND today is the 6th or later.
        """
        from django.utils import timezone
        now = timezone.now()
        if now.day < 6:
            return False
        if not self.balance_approved_at:
            return False
        return (
            self.balance_approved_at.year == now.year
            and self.balance_approved_at.month == now.month
        )

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

    STATUS_PENDING     = 'pending'
    STATUS_PROCESSING  = 'processing'   # OCR running
    STATUS_REVIEW      = 'under_review' # waiting for SE
    STATUS_APPROVED    = 'approved'
    STATUS_REJECTED    = 'rejected'
    STATUS_CHOICES     = [
        (STATUS_PENDING,    'Pending Submission'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_REVIEW,     'Under SE Review'),
        (STATUS_APPROVED,   'Approved'),
        (STATUS_REJECTED,   'Rejected'),
    ]

    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='kyc')
    # ── Personal ─────────────────────────────────────────────────────────
    full_name        = models.CharField(max_length=150, help_text='Real name as on your ID document')
    date_of_birth    = models.DateField(null=True, blank=True, help_text='DOB as on your ID document')
    phone            = models.CharField(max_length=30)
    contact_address  = models.CharField(max_length=255)
    country          = models.CharField(max_length=100)
    id_type          = models.CharField(max_length=20, choices=ID_CHOICES, default=ID_NATIONAL)
    id_number        = models.CharField(max_length=60)
    id_document      = models.ImageField(upload_to='kyc/id_docs/', blank=True, help_text='Legacy single-image field')
    id_front         = models.ImageField(upload_to='kyc/fronts/', blank=True, help_text='Front of ID')
    id_back          = models.ImageField(upload_to='kyc/backs/',  blank=True, null=True,
                           help_text='Back of ID (not required for passport)')
    # ── Payment ──────────────────────────────────────────────────────────
    payment_method   = models.CharField(max_length=20, choices=PAY_CHOICES, default=PAY_BANK)
    account_holder   = models.CharField(max_length=150, blank=True)
    bank_name        = models.CharField(max_length=150, blank=True)
    account_number   = models.CharField(max_length=60,  blank=True)
    swift_code       = models.CharField(max_length=11,  blank=True)
    bank_country     = models.CharField(max_length=100, blank=True)
    paypal_email     = models.EmailField(blank=True)
    # ── OCR results ──────────────────────────────────────────────────────
    ocr_name         = models.CharField(max_length=200, blank=True)
    ocr_dob          = models.DateField(null=True, blank=True)
    ocr_id_number    = models.CharField(max_length=100, blank=True)
    ocr_raw          = models.JSONField(default=dict, blank=True)
    # ── Match scores (0-100) ──────────────────────────────────────────────
    name_match_score    = models.FloatField(null=True, blank=True)
    dob_match           = models.BooleanField(null=True, blank=True)
    overall_match_score = models.FloatField(null=True, blank=True)
    age_valid           = models.BooleanField(null=True, blank=True)  # 18 <= age <= 50
    # ── Status ───────────────────────────────────────────────────────────
    status           = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING)
    rejection_reason = models.TextField(blank=True)
    admin_notes      = models.TextField(blank=True)
    reviewed_by      = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='kyc_reviews', limit_choices_to={'role__in': ['se', 'ce', 'admin']},
    )
    submitted_at     = models.DateTimeField(auto_now_add=True)
    reviewed_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'author_kyc'

    def __str__(self):
        return f'KYC: {self.user.username} [{self.status}]'


class BlacklistedIP(models.Model):
    ip_address     = models.GenericIPAddressField(unique=True)
    reason         = models.TextField(blank=True)
    blacklisted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='ip_blacklists',
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'blacklisted_ips'

    def __str__(self):
        return f'Blocked IP: {self.ip_address}'


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


class UserDevice(models.Model):
    """Tracks every physical device a user has logged in from."""
    PLATFORM_ANDROID = 'android'
    PLATFORM_IOS     = 'ios'
    PLATFORM_CHOICES = [
        (PLATFORM_ANDROID, 'Android'),
        (PLATFORM_IOS,     'iOS'),
    ]

    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='devices',
    )
    device_id  = models.CharField(max_length=255, db_index=True)
    platform   = models.CharField(max_length=10, choices=PLATFORM_CHOICES, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table       = 'user_devices'
        unique_together = [('user', 'device_id')]
        ordering        = ['-last_seen']

    def __str__(self):
        return f'{self.user.username} — {self.platform} — {self.device_id[:16]}'