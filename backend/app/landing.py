import html

from app.settings_store import consent_url, offer_url, privacy_url
from app.telegram_link import bot_start_url, bot_username


def render_home() -> str:
    bot_url = bot_start_url()
    bot_label = f"@{bot_username()}" if bot_username() else "Telegram-бот"
    cta = (
        f'<a class="cta" href="{html.escape(bot_url)}" rel="noopener">Открыть в Telegram</a>'
        if bot_url
        else f'<span class="cta cta-muted">{html.escape(bot_label)}</span>'
    )
    privacy = privacy_url() or "/privacy"
    consent = consent_url() or "/consent"
    offer = offer_url() or "/offer"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Aimarket — единый API-ключ к лучшим ИИ-моделям. Оплата по факту использования, пополнение в рублях.">
  <title>Aimarket — API к ИИ-моделям</title>
  <link rel="icon" type="image/png" href="/favicon-96x96.png" sizes="96x96">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="shortcut icon" href="/favicon.ico">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">
  <meta name="theme-color" content="#1c1915">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      background: #f4f1ea;
      color: #1c1915;
      font: 16px/1.55 "Segoe UI", system-ui, sans-serif;
    }}
    a {{ color: inherit; text-decoration: none; }}
    .page {{ flex: 1; display: flex; flex-direction: column; }}
    .hero {{
      flex: 1;
      width: min(1120px, 100%);
      margin: 0 auto;
      padding: 32px 24px 56px;
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
      gap: 40px;
      align-items: center;
    }}
    .brand {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 28px;
      font-weight: 700;
      letter-spacing: -0.03em;
      font-size: 18px;
    }}
    .brand img {{
      width: 36px;
      height: 36px;
      border-radius: 10px;
      box-shadow: 0 8px 24px rgba(28, 25, 21, 0.08);
    }}
    h1 {{
      margin: 0 0 16px;
      font-size: clamp(2rem, 4vw, 3.1rem);
      line-height: 1.08;
      letter-spacing: -0.04em;
      max-width: 11ch;
    }}
    .lead {{
      margin: 0 0 28px;
      max-width: 42rem;
      color: #4f473d;
      font-size: 1.05rem;
    }}
    .features {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 32px;
    }}
    .feature {{
      padding: 14px 12px;
      border: 1px solid rgba(28, 25, 21, 0.08);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.45);
    }}
    .feature img {{
      width: 44px;
      height: 44px;
      border-radius: 12px;
      display: block;
      margin-bottom: 10px;
    }}
    .feature strong {{
      display: block;
      margin-bottom: 4px;
      font-size: 0.95rem;
    }}
    .feature span {{
      display: block;
      color: #6b645b;
      font-size: 0.88rem;
      line-height: 1.4;
    }}
    .cta {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 48px;
      padding: 0 22px;
      border-radius: 999px;
      background: #1c1915;
      color: #f4f1ea;
      font-weight: 600;
      box-shadow: 0 14px 30px rgba(28, 25, 21, 0.16);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .cta:hover {{
      transform: translateY(-1px);
      box-shadow: 0 18px 36px rgba(28, 25, 21, 0.18);
    }}
    .cta-muted {{
      opacity: 0.72;
      box-shadow: none;
    }}
    .hero-visual img {{
      width: 100%;
      border-radius: 24px;
      border: 1px solid rgba(28, 25, 21, 0.08);
      box-shadow: 0 24px 60px rgba(28, 25, 21, 0.12);
      display: block;
    }}
    .footer {{
      border-top: 1px solid rgba(28, 25, 21, 0.08);
      background: rgba(255, 255, 255, 0.35);
    }}
    .footer-inner {{
      width: min(1120px, 100%);
      margin: 0 auto;
      padding: 22px 24px 28px;
      display: flex;
      flex-wrap: wrap;
      gap: 12px 24px;
      align-items: center;
      justify-content: space-between;
      color: #6b645b;
      font-size: 0.92rem;
    }}
    .footer-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 18px;
    }}
    .footer-links a {{
      text-decoration: underline;
      text-underline-offset: 3px;
    }}
    @media (max-width: 900px) {{
      .hero {{
        grid-template-columns: 1fr;
        padding-top: 20px;
      }}
      .hero-visual {{ order: -1; }}
      .features {{ grid-template-columns: 1fr; }}
      h1 {{ max-width: none; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="hero-copy">
        <div class="brand">
          <img src="/favicon-96x96.png" width="36" height="36" alt="">
          <span>Aimarket</span>
        </div>
        <h1>Единый ключ к&nbsp;лучшим ИИ-моделям</h1>
        <p class="lead">
          Пополняйте баланс картой в рублях, получайте API-токен в Telegram и
          подключайте OpenAI-, Anthropic- и Google-совместимые приложения без абонентской платы.
        </p>
        <div class="features">
          <article class="feature">
            <img src="/home-feature-key.jpg" alt="">
            <strong>Один токен</strong>
            <span>Один ключ для Codex, Claude, Cursor и других программ.</span>
          </article>
          <article class="feature">
            <img src="/home-feature-pay.jpg" alt="">
            <strong>Оплата по факту</strong>
            <span>Списание только за реальные запросы к API.</span>
          </article>
          <article class="feature">
            <img src="/home-feature-models.jpg" alt="">
            <strong>Разные форматы</strong>
            <span>OpenAI Chat Completions, Claude Messages и другие протоколы.</span>
          </article>
        </div>
        {cta}
      </div>
      <div class="hero-visual">
        <img src="/home-hero.jpg" alt="Схема подключения Aimarket к ИИ-моделям">
      </div>
    </section>
    <footer class="footer">
      <div class="footer-inner">
        <span>© Aimarket</span>
        <nav class="footer-links" aria-label="Документы">
          <a href="{html.escape(privacy)}">Политика конфиденциальности</a>
          <a href="{html.escape(consent)}">Согласие на обработку данных</a>
          <a href="{html.escape(offer)}">Публичная оферта</a>
        </nav>
      </div>
    </footer>
  </div>
</body>
</html>"""
