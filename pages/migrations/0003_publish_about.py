from django.db import migrations


def publish_about(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    Page.objects.filter(slug="about").update(is_published=True)


class Migration(migrations.Migration):
    dependencies = [("pages", "0002_seed_pages")]
    operations = [migrations.RunPython(publish_about, migrations.RunPython.noop)]
