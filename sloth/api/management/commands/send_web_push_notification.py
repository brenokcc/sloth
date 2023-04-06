import json

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from pywebpush import webpush


class Command(BaseCommand):

    def handle(self, *args, **options):
        user = User.objects.get(username='admin')
        print(webpush(
            subscription_info=json.loads(user.push_notification.subscription),
            data="Hello World!",
            vapid_private_key="GoFJpuTAdhepzfxOHdrW7u2ONh7V8ZIjPkjgpWSS3ks",
            vapid_claims={"sub": "mailto:admin@admin.com"}
        ))
