from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE UNIQUE INDEX IF NOT EXISTS unique_user_email ON auth_user (LOWER(email));",
            reverse_sql="DROP INDEX IF EXISTS unique_user_email;",
        ),
    ]
