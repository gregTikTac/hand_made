from django.db import migrations

ABOUT = """Всем привет, меня зовут Екатерина Зуева @baloo_hand

Я мастер с шестилетним стажем: вяжу игрушки и создаю схемы.

Здесь вы найдёте более 80 моих авторских мастер-классов на самые милые игрушки крючком.

Почти все мои игрушки цельновязанные: тело и голова — одна деталь, ручки и ножки ввязываются в процессе. В каждом PDF — список материалов, подробное описание вязания и сборки игрушки, множество фотографий процесса, и в некоторых мастер-классах есть видео более сложных моментов.

Желаю вам получить удовольствие от вязания игрушек по моим мастер-классам и лёгких петелек!"""


def seed(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    pages = [
        ("about", "Об авторе", ABOUT),
        ("offer", "Публичная оферта", ""),
        ("privacy", "Политика конфиденциальности", ""),
        ("pdn-consent", "Согласие на обработку персональных данных", ""),
    ]
    for slug, title, body in pages:
        Page.objects.get_or_create(
            slug=slug, defaults={"title": title, "body": body, "is_published": False}
        )


class Migration(migrations.Migration):
    dependencies = [("pages", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
