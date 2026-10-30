"""Static page views."""

from django.shortcuts import render


def home(request):
    """Главная страница (заглушка на этапе 1)."""
    return render(
        request,
        "pages/home.html",
        {
            "products": [
                {
                    "title": "Мастер-класс «Лисичка»",
                    "price": 450,
                    "old_price": None,
                    "badge": None,
                    "color": 1,
                },
                {
                    "title": "Козлёнок Боря",
                    "price": 450,
                    "old_price": 450,
                    "badge": "preorder",
                    "color": 2,
                },
                {
                    "title": "Мастер-класс «Плюшевые копытца»",
                    "price": 420,
                    "old_price": 600,
                    "badge": "sale",
                    "color": 3,
                },
                {
                    "title": "Забавные овечки",
                    "price": 400,
                    "old_price": None,
                    "badge": "combo",
                    "color": 4,
                },
            ]
        },
    )
