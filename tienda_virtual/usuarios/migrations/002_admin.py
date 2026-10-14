from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_admin(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "admin@admin.com",
            "password": make_password("admin"),
            "is_superuser": True,
            "is_staff": True,
        }
    )

def delete_admin(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    User.objects.filter(username="admin").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_admin, delete_admin),
    ]
