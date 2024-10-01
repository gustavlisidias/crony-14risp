import os
from urllib.parse import urljoin

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class CKEditorUploader(FileSystemStorage):
	'''Custom storage for django_ckeditor_5 images.'''

	location = os.path.join(settings.MEDIA_ROOT, 'ckeditor/upload/')
	base_url = urljoin(settings.MEDIA_URL, 'ckeditor/upload/')
