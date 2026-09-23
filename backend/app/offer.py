import html

from app.settings_store import get_setting, offer_url

_DEFAULT = """
1. Общие положения

Настоящий документ — публичная оферта на предоставление доступа к API нейросетей через сервис Aimarket. Акцепт оферты — нажатие кнопки согласия в Telegram-боте Aimarket.

2. Предмет

Исполнитель открывает заказчику доступ к моделям через отдельный API-ключ. Ключ работает как OpenAI-совместимый ключ. Лимит ключа равен остатку баланса заказчика и уменьшается по мере запросов.

3. Баланс и цена

Баланс ведётся в долларах США и совпадает с лимитом ключа. Рубли пересчитываются в доллары по цене, указанной в боте на момент заявки. Заявка зачисляется после проверки оплаты. Потраченный лимит не возвращается. Неиспользованный остаток можно перенести на новый ключ при перевыпуске.

4. Ключ

Ключ показывается один раз. Его хранит заказчик. Перевыпуск удаляет прежний ключ и создаёт новый с тем же оставшимся лимитом. Запросы со старым ключом после этого не проходят.

5. Ограничения

Нельзя передавать ключ третьим лицам для перепродажи, обходить лимит и использовать доступ для противоправных действий. Исполнитель может приостановить ключ, если лимит исчерпан или доступ используется с нарушением оферты.

6. Ответственность

Доступ предоставляется в том объёме, в каком его даёт поставщик моделей. Перерыв на стороне поставщика не является простоем по вине исполнителя, лимит за неуспешные запросы поставщик не списывает.
""".strip()


def render_offer() -> str:
    custom = get_setting("offer_text").strip()
    body = custom or _DEFAULT
    seller = get_setting("seller_name").strip() or "Aimarket"
    inn = get_setting("seller_inn").strip() or "не указан"
    email = get_setting("seller_email").strip() or "не указан"
    paragraphs = "".join(f"<p>{html.escape(part.strip())}</p>" for part in body.split("\n\n") if part.strip())
    link = offer_url() or "/offer"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>Оферта — Aimarket</title>
  <style>
    body {{ margin: 0; background: #f4f1ea; color: #1c1915; font: 17px/1.55 Georgia, "Times New Roman", serif; }}
    main {{ max-width: 720px; margin: 0 auto; padding: 48px 20px 72px; }}
    h1 {{ font: 600 32px/1.15 "Segoe UI", sans-serif; letter-spacing: -0.03em; margin: 0 0 8px; }}
    .meta {{ font: 14px/1.4 "Segoe UI", sans-serif; color: #6b645b; margin-bottom: 28px; }}
    p {{ margin: 0 0 16px; }}
    a {{ color: inherit; }}
  </style>
</head>
<body>
  <main>
    <h1>Публичная оферта</h1>
    <p class="meta">{html.escape(seller)} · ИНН {html.escape(inn)} · {html.escape(email)}</p>
    {paragraphs}
    <p class="meta">Согласие даётся в Telegram-боте Aimarket. Эта страница: {html.escape(link)}</p>
  </main>
</body>
</html>"""
