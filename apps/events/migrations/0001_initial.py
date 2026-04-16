import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField()),
                ("language", models.CharField(db_index=True, max_length=50)),
                ("location", models.CharField(db_index=True, max_length=255)),
                ("starts_at", models.DateTimeField(db_index=True)),
                ("ends_at", models.DateTimeField()),
                ("capacity", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["starts_at"],
            },
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(fields=["starts_at"], name="events_even_starts__b96432_idx"),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(fields=["language"], name="events_even_languag_86a4f3_idx"),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(fields=["location"], name="events_even_locatio_c9b7e5_idx"),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(fields=["created_by"], name="events_even_created_2f8d12_idx"),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(
                fields=["starts_at", "language", "location"],
                name="events_even_starts__composite_idx",
            ),
        ),
    ]
