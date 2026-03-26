# django-media-manager

A reusable Django app for media uploads, albums, categories, and moderation.
Works with any project's custom User model via `AUTH_USER_MODEL`.

## Features

- Image, video, document, and audio file handling
- Auto-detection of file type, size, MIME type
- Generic foreign key attachment to any model
- Album system with ordered media
- Privacy controls (public / friends / private)
- Moderation flags (approved, flagged, featured)
- Location metadata and EXIF-ready fields
- `django-taggit` tags
- Admin with image preview, bulk actions, and inline album editor

---

## Installation

### From GitHub (recommended for private use)

```bash
pip install git+https://github.com/YOUR_USERNAME/django-media-manager.git
```

To pin to a specific version/commit:

```bash
pip install git+https://github.com/YOUR_USERNAME/django-media-manager.git@v0.1.0
```

### Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    ...
    'taggit',
    'media_manager',
]
```

### Run migrations

```bash
python manage.py migrate
```

---

## Requirements

- Django >= 4.2
- Pillow >= 10.0
- django-taggit >= 4.0
- django-storages >= 1.14 (optional — only needed for S3/Cloudinary backends)

For S3:
```bash
pip install "django-media-manager[s3] @ git+https://github.com/YOUR_USERNAME/django-media-manager.git"
```

For Cloudinary:
```bash
pip install "django-media-manager[cloudinary] @ git+https://github.com/YOUR_USERNAME/django-media-manager.git"
```

---

## Settings

No required settings. The app uses `settings.AUTH_USER_MODEL` automatically.

Optional storage backend setting on each `Media` record (field: `storage_backend`).
Configure `django-storages` as normal in your project settings.

---

## Migrating an existing project (e.g. travel-site)

If you previously had a local `media` or `media_app` Django app with the same
models, follow these steps to replace it with this package without losing data.

### 1. Install the package

```bash
pip install git+https://github.com/YOUR_USERNAME/django-media-manager.git
```

### 2. Update INSTALLED_APPS

```python
# Before
'media_app',

# After
'media_manager',
```

### 3. Fake the initial migration

The database tables already exist — you just need Django to think it ran
the migration without actually touching the tables:

```bash
python manage.py migrate media_manager --fake-initial
```

### 4. Update all imports in your project

```python
# Before
from media_app.models import Media, MediaAlbum, AlbumMedia, MediaCategory
from media.models import Media  # if app was named 'media'

# After
from media_manager.models import Media, MediaAlbum, AlbumMedia, MediaCategory
```

### 5. Delete the old app folder

Once confirmed working, remove the old `media_app/` or `media/` directory
from your project and delete its entry from `INSTALLED_APPS`.

---

## Usage

### Attach media to any model

```python
from media_manager.models import Media

# Generic FK — attach to a Trip, Review, Post, anything
media = Media.objects.get(pk=1)
media.content_object = my_trip_instance
media.save()

# Query all media attached to a specific object
from django.contrib.contenttypes.models import ContentType
ct = ContentType.objects.get_for_model(Trip)
trip_media = Media.objects.filter(content_type=ct, object_id=trip.pk)
```

### Create an album

```python
from media_manager.models import MediaAlbum, AlbumMedia

album = MediaAlbum.objects.create(user=request.user, title="Summer 2025")
AlbumMedia.objects.create(album=album, media=photo, display_order=1)
```

---

## Versioning

This project follows semantic versioning: `MAJOR.MINOR.PATCH`

- PATCH: bug fixes
- MINOR: new fields or features (backward-compatible)
- MAJOR: breaking model changes requiring manual migration work
