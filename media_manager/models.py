# media_manager/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from taggit.managers import TaggableManager

import os
import uuid
import mimetypes


# ---------------------------------------------------------------------------
# Bundled base model — no external dependency on any project's core app
# ---------------------------------------------------------------------------

class TimeStampedModel(models.Model):
    """Abstract base model providing created_at and updated_at timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Upload path helpers
# ---------------------------------------------------------------------------

def user_media_upload_path(instance, filename):
    """Upload to: users/{user_id}/{year}/{month}/{uuid}.{ext}"""
    from django.utils import timezone
    now = timezone.now()
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    return f"users/{instance.uploaded_by.id}/{now.year}/{now.month:02d}/{new_filename}"


def site_media_upload_path(instance, filename):
    """Upload to: site/{content_type}/{year}/{month}/{uuid}.{ext}"""
    from django.utils import timezone
    now = timezone.now()
    content_type = instance.content_type.model if instance.content_type else 'general'
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    return f"site/{content_type}/{now.year}/{now.month:02d}/{new_filename}"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class MediaCategory(TimeStampedModel):
    """Categories for organizing media."""

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="E.g., Trip Photos, Reviews, Profile Pictures, Activity Images"
    )
    description = models.TextField(blank=True)
    is_system_category = models.BooleanField(
        default=False,
        help_text="System-reserved category — do not delete."
    )

    class Meta:
        db_table = 'media_categories'
        verbose_name_plural = 'Media Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Media(TimeStampedModel):
    """A single uploaded media file (image, video, document, or audio)."""

    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('audio', 'Audio'),
    ]

    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
    ]

    IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic'}
    VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
    DOCUMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

    # -- File --
    file = models.FileField(upload_to=user_media_upload_path, max_length=500)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES, blank=True, db_index=True)

    # Auto-detected
    file_size = models.BigIntegerField(help_text="File size in bytes", null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    file_extension = models.CharField(max_length=10, blank=True)

    # Image dimensions
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)

    # Video
    duration = models.IntegerField(null=True, blank=True, help_text="Duration in seconds")

    # Thumbnail (for videos/documents)
    thumbnail = models.ImageField(upload_to='thumbnails/%Y/%m/', null=True, blank=True)

    # -- Ownership --
    # Swappable: respects AUTH_USER_MODEL in each project
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_media'
    )
    is_user_generated = models.BooleanField(
        default=True,
        help_text="True for user uploads, False for site/admin content"
    )

    # -- Generic attachment (optional) --
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True, blank=True,
        help_text="Type of object this media is attached to"
    )
    object_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="ID of the object this media is attached to"
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    # -- Categorization --
    category = models.ForeignKey(
        MediaCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='media_files'
    )
    tags = TaggableManager(blank=True)

    # -- Metadata --
    title = models.CharField(max_length=200, blank=True)
    caption = models.TextField(blank=True)
    alt_text = models.CharField(max_length=200, blank=True, help_text="Alt text for accessibility")

    # -- Location --
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_name = models.CharField(max_length=200, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True, help_text="When the photo/video was taken")

    # -- Privacy & moderation --
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')
    is_featured = models.BooleanField(default=False, help_text="Featured in galleries/homepage")
    is_approved = models.BooleanField(default=True, help_text="Approved by moderators")
    is_flagged = models.BooleanField(default=False, help_text="Flagged for review")
    flagged_reason = models.TextField(blank=True)
    display_order = models.IntegerField(default=0, help_text="Order in galleries/albums")

    # -- Stats --
    view_count = models.IntegerField(default=0)
    download_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)

    # -- Storage --
    storage_backend = models.CharField(
        max_length=50,
        default='local',
        help_text="Storage backend: local, s3, cloudinary, etc."
    )

    class Meta:
        db_table = 'media'
        verbose_name_plural = 'Media'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uploaded_by', '-created_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['media_type', 'is_approved']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        display = self.title or (os.path.basename(self.file.name) if self.file else '(no file)')
        return f"{display} by {self.uploaded_by}"
    
    # -- Properties --

    @property
    def file_size_mb(self):
        """File size in MB, rounded to 2 decimal places."""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None

    # -- Helpers --

    def is_attached(self):
        return self.content_type_id is not None and self.object_id is not None

    def attached_object_exists(self):
        if not self.is_attached():
            return False
        return self.content_object is not None

    # -- Lifecycle --

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            self.file_extension = os.path.splitext(self.file.name)[1].lower().lstrip('.')
            mime, _ = mimetypes.guess_type(self.file.name)
            self.mime_type = mime or ''

            if not self.media_type:
                if self.file_extension in self.IMAGE_EXTENSIONS:
                    self.media_type = 'image'
                elif self.file_extension in self.VIDEO_EXTENSIONS:
                    self.media_type = 'video'
                elif self.file_extension in self.DOCUMENT_EXTENSIONS:
                    self.media_type = 'document'

        super().save(*args, **kwargs)


class MediaAlbum(TimeStampedModel):
    """An ordered collection of media files belonging to a user."""

    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='media_albums'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default='public')

    cover_image = models.ForeignKey(
        Media,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cover_for_albums'
    )

    view_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'media_albums'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.user}"

    @property
    def media_count(self):
        return self.album_media_items.count()


class AlbumMedia(TimeStampedModel):
    """Through model for the MediaAlbum ↔ Media many-to-many relationship."""

    album = models.ForeignKey(MediaAlbum, on_delete=models.CASCADE, related_name='album_media_items')
    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='album_memberships')
    display_order = models.IntegerField(default=0)
    caption = models.TextField(blank=True, help_text="Album-specific caption (overrides media caption)")

    class Meta:
        db_table = 'album_media'
        unique_together = [['album', 'media']]
        ordering = ['album', 'display_order']

    def __str__(self):
        return f"{self.media} in {self.album.title}"
