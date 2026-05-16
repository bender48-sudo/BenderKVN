# ПОЛНЫЙ КОНТЕКСТ ПРОЕКТА: VPN-сервис для РФ
## Дата: 29 марта 2026 | Для переноса в новый чат

---

# ЧАСТЬ 1. КЛЮЧЕВЫЕ РЕШЕНИЯ

[DECISION] Целевая аудитория: Россия, обход блокировок РКН/ТСПУ. 200+ юзеров, подписка 149₽/мес.

[DECISION] Протокол: VLESS + XTLS Reality + Vision (основной), XHTTP (fallback). НЕ WireGuard (блокируется 100%), НЕ OpenVPN (блокируется 100%). AmneziaWG 2.0 — запасной вариант.

[DECISION] Критически важно по SNI: НЕ использовать Google, Yandex, VK, Bing, Microsoft, Apple, iCloud — все палятся ТСПУ (подтверждено февраль 2026). Только малоизвестные зарубежные домены, подобранные RealiTLScanner под конкретную подсеть хостера. Пример рабочего: pdf24.org на Hetzner.

[DECISION] Клиент: Happ (App Store / Google Play) — поддерживает VLESS Reality, подписки с автообновлением, автопинг, автоподключение к лучшему серверу. Позже — форк клиента с бесшовным переключением серверов.

[DECISION] Стек управления (рекомендация от знающего человека, принята):
- **Remnawave** (docs.rw) — панель управления VPN, юзеры, ноды, конфиги
- **Beszel** (beszel.dev) — мониторинг серверов
- **Reshala** (github.com/DonMatteoVPN/Reshala-Remnawave-Bedolaga) — лимиты трафика per user + нагрузочное тестирование (~120 юзеров на ноду)
- **remna-shop** (github.com/catoo-hub/remna-shop) — Telegram-бот для продажи подписок
- **mtg** — MTProto proxy для Telegram

---

# ЧАСТЬ 2. АРХИТЕКТУРА

## Двухуровневая система подключения

### Уровень 1 (80% юзеров): Прямое подключение
```
Юзер (Happ) → VLESS Reality → Зарубежный сервер → Интернет
```
Для: проводной интернет, мобильный без белых списков.
Протокол: VLESS + XTLS-RPRX-VISION + Reality
Транспорт: TCP (основной) + XHTTP (fallback)
SNI: малоизвестные зарубежные домены
Fingerprint: chrome (uTLS)
Порт: 443

### Уровень 2 (20% юзеров, при шатдаунах): Через российский relay
```
Юзер (Happ) → Российский relay (белый IP) → Зарубежный exit → Интернет
```
На relay обязателен реальный сайт-прикрытие (IP-чекер/speedtest), чтобы хостер не заблокировал за VPN-трафик.

ВАЖНО (свежее из Хабра, март 2026): прямое подключение VLESS Reality к Европе сейчас «шейпится» ТСПУ — не обрывает сессию, а замораживает после 15-20 КБ данных. Chain через российскую ноду может стать основным способом. На relay рекомендуют XHTTP в режиме packet-up.

## Белый список РФ (SNI для relay)
Источники: github.com/hxehex/russia-mobile-internet-whitelist, github.com/VasiliyBP/rmi-whitelist

Рабочие домены:
- yandex.ru, yandex.net, yastatic.net, cdn.yandex.net
- vk.com, vkuser.net, mycdn.me (CDN Одноклассников)
- sberbank.ru, online.sberbank.ru
- gosuslugi.ru
- 2gis.com, ozon.ru, avito.ru
- okko.tv, start.film, premier.one
- ngenix.net (CDN)
- ads.x5.ru (реклама Пятёрочки — подтверждено TunnelGuard и Kovanoff VPN)
- mail.ru, my.mail.ru

Проблема: операторы переходят на комбинированную модель IP + SNI — даже с правильным SNI блокируют если IP не из белого списка.

## Smart Balancer (наша доработка)

Все серверы работают одновременно, нет «основных» и «резервных». API мониторит каждые 30 сек: CPU, RAM, пинг, трафик. Формирует subscription отсортированный по «здоровью» (формула весов). Happ на клиенте сам выбирает лучший пинг. Нода упала → API убирает за 30 сек → Happ переключается автоматом → бот алертит админу.

Формула веса: (100 - CPU%) × 0.4 + (100 - RAM%) × 0.2 + (ping_ok ? 30 : 0) + (трафик_остаток > 20% ? 10 : 0)

## Доработки поверх стека (фазы)
- Фаза 1 (MVP): Remnawave + ноды + бот + Happ подписки
- Фаза 2: Форк клиента — бесшовное переключение серверов через API, healthcheck каждые 30 сек
- Фаза 3: Бриджирование в стиле Geph — клиент пробует несколько путей одновременно, серверная балансировка нагрузки

---

# ЧАСТЬ 3. СЕРВЕРЫ

## Текущий сервер (арендован и работает)
- **BitLaunch**, Amsterdam, $22/мес, 2 CPU / 2GB RAM / Unlimited transfer
- IP: 168.100.11.140
- ОС: Ubuntu 22.04
- SSH-ключ: добавлен при создании
- Оплата: крипта (USDT Polygon → LTC через FixedFloat → BitLaunch)
- Статус: запущен, ожидает деплой Remnawave

## Заблокированные аккаунты
- **Hetzner** — заблокировали аккаунт (регистрация на «Vinni Puh»). Можно попробовать заново с реальными данными.
- **DigitalOcean** — заблокировали аккаунт (антифрод при оплате криптой). Отказ окончательный.

## Список провайдеров на будущее
Проверенные с криптой:
- **BitLaunch** (bitlaunch.io) — используем, прослойка для Vultr/DO/Linode, крипта без KYC
- **FriendHosting** (friendhosting.net) — много EU-локаций (Latvia, Poland, Netherlands, Czech, Germany, Bulgaria, Romania, Switzerland, Italy, Greece), €9.49/мес за 2vCPU/2GB/1Gbps

Рекомендации от знающих людей:
- ishosting
- 1cent
- Play2Go
- Intensio
- Яндекс Cloud (для relay — IP в белых списках)
- Cloudrix
- ServHost
- HipHosting (без поддержки)
- vdska
- Vultr (крипта через CoinGate)

Не подошли:
- ServerSpace (my.serverspace.io) — дорого, €127/мес за 1 Gbps канал
- LeaseWeb — enterprise, сложная регистрация, дорого

## Расчёт мощности
Один сервер (2 CPU / 2GB RAM / 1 Gbps):
- YouTube 1080p (~10 Mbps/юзер): до 100 одновременно онлайн
- Сёрфинг + мессенджеры (~5 Mbps): до 200 онлайн
- YouTube 4K (~20 Mbps): до 50 онлайн
- Reshala говорит ~120 юзеров на ноду
- 200 подписчиков → 60-100 одновременно онлайн (30-50% пика)
- Лимитирующий фактор — ширина канала 1 Gbps, не CPU/RAM

---

# ЧАСТЬ 4. РАЗБОР КОНКУРЕНТОВ

## SafeVPN (safevpnbot.com)
Subscription URL: safevpnbot.com/sub/?i={user_id}-{key}
Конфиги (получены из реальной подписки):
- Основной: xe8k5fxn.safevpnbot.com:443 — VLESS Reality, SNI=google-analytics.com, fp=chrome
- Резерв: тот же хост, порт 2053, SNI=pimg.mycdn.me (CDN Одноклассников)
- Россия: 81.90.31.181:8080 — gRPC Reality, SNI=ya.ru
- Европа: 89.125.209.49:8443 — VLESS Reality, SNI=deepl.com
- США: 45.41.207.219:443 — VLESS Reality, SNI=icloud.com, pbk другой
Клиент: Happ (iOS/Android/macOS)
Модель: Telegram-бот → подписка → Happ

## TunnelGuard (tunnelguard.ru)
Subscription URL: kosmos.tunnelguard.ru/link.php?client_id={uuid}
Конфиги (получены из реальной подписки):
- «Мобильный обход»: 51.250.69.157:443 — VLESS Reality, SNI=ads.x5.ru, fp=qq (!) — сервер в Яндекс.Облаке
- Молдова: mle.tunnelguard.ru:443 — VLESS TLS, SNI=mle.tunnelguard.ru, fp=safari
- Польша: pla.tunnelguard.ru:443 — VLESS XHTTP (!) с padding, SNI=pla.tunnelguard.ru
- Латвия: lvb.tunnelguard.ru:443 — VLESS XHTTP
- Хельсинки: hla.tunnelguard.ru:443 — VLESS XHTTP
- Нидерланды: nla.tunnelguard.ru:443 — VLESS XHTTP
Важно: используют XHTTP (новый транспорт) на большинстве серверов + свои домены с TLS

## Kovanoff VPN (maptap.ru)
Subscription URL: maptap.ru/sub/{uuid} (отдаёт конфиги только с правильным User-Agent)
Конфиг «АНТИ-БелыйСписок»:
- 158.160.125.163:57822 — VLESS Reality, SNI=ads.x5.ru, fp=random
- IP из подсети Яндекс.Облака (158.160.x.x) — в белом списке
- Нестандартный порт 57822 (не 443)
- Short ID: c3 (1 байт)

## BlackTemple (BLACKTEMPLE-SPACE)
- 300+ выделенных серверов
- Дата-центры: DigitalOcean, OVH, Hetzner, M9
- Тарифы от 1 рубля в сутки
- Работают 3 года

## Amnezia Premium (конкурент)
- 20 локаций, 470K+ юзеров
- Наше УТП vs них: авто-ротация при блокировке, цена ниже, Telegram-first

---

# ЧАСТЬ 5. КЛИЕНТ (Happ)

Happ - Proxy Utility
- App Store (iOS 15+), Google Play (Android 5+), macOS desktop
- 11 млн скачиваний, рейтинг 4.15
- Протоколы: VLESS Reality, VMess, Trojan, Shadowsocks, Socks, Hysteria2
- Ключевые фичи для нас:
  - Subscriptions с автообновлением
  - Автоподключение к серверу с наименьшим пингом (subscription-autoconnect-type: lowestdelay)
  - Fallback URL если основной домен заблокирован
  - Скрытые и зашифрованные подписки
  - Автопинг при открытии (subscription-ping-onopen-enabled: 1)
  - Resolve DNS через кастомный сервер
  - Per-app proxy (routing по приложениям)

Документация для разработчиков: happ.su/main/dev-docs/app-management

Subscription формат — plain text, каждая строка = vless:// ссылка. HTTP-заголовки ответа управляют поведением клиента.

---

# ЧАСТЬ 6. ИССЛЕДОВАННЫЕ ТЕХНОЛОГИИ

## Geph (geph.io) — изучен, отложен
Код клиента скачан и разобран (geph4-client-master.zip).
Плюсы: автоматическая система бриджей, sosistab2 протокол (устойчив к active probing).
Минусы: закрытая экосистема (нужен свой binder/broker + exits + bridges), сложный Rust-код с 11+ кастомными крейтами, нереально форкнуть за 2 недели.
Решение: идеи бриджей заложены в фазу 3, но реализуем проще через Happ subscription + API балансировку.

Geph5 (новая версия): broker вместо binder, JSON-RPC API, MPL 2.0 лицензия, config files вместо CLI args.

## AmneziaWG 2.0 — рассмотрен, отложен как запасной
Клиент в App Store принимает .conf файлы, но нет автообновления подписок как в Happ.
Хорош для обхода DPI через рандомизацию заголовков, но VLESS Reality мощнее для РФ.

## User-Agent Switcher — отложен
Для VPN не нужен отдельно. uTLS в VLESS Reality уже подменяет fingerprint (Chrome/Firefox). Отдельный UA-switcher — это про антидетект-браузеры (другой продукт).

---

# ЧАСТЬ 7. ТЕКУЩАЯ ОБСТАНОВКА (март 2026)

## Блокировки
- РКН заблокировал 469 VPN-сервисов к февралю 2026, рост 70% за 3 месяца
- С декабря 2025 блокируют протоколы: SOCKS5, VLESS, L2TP
- РКН планирует ИИ-систему за 2.3 млрд руб для фильтрации трафика
- ТСПУ детектит Reality по несовпадению SNI и IP/ASN сервера
- 24 января 2026 массово легли VPN через российские облака — РКН научился вычислять

## Что работает (февраль-март 2026)
- VLESS Reality с малоизвестными зарубежными SNI — работает на проводном
- XHTTP — следующий шаг, маскирует под HTTP/2 запросы
- AmneziaWG 2.0 — работает
- Chain через RU-relay → EU-exit — самый надёжный для мобильного

## Белые списки
- С осени 2025 мобильные операторы при шатдаунах оставляют только одобренные сайты
- 120+ сервисов в белом списке на март 2026
- Пока только мобильный трафик, проводной не затронут
- Операторы переходят на комбинированную модель IP + SNI

## Правовая ситуация
- VPN в РФ формально не запрещён
- VPN-сервис обязан ограничивать доступ к запрещённым сайтам
- Нельзя рекламировать VPN как средство обхода блокировок
- Штраф за рекламу VPN: до 500К руб юрлицам
- Большинство VPN-сервисов для РФ не регистрируются в России — принимают крипту через Telegram-бот

---

# ЧАСТЬ 8. ЭКОНОМИКА

## Расходы (план)
- 4 VPN-ноды: ~$60-80/мес (зависит от провайдера)
- 2 RU relay: ~$11/мес (~1000₽)
- 1 API-сервер: ~$5/мес
- Итого: ~$75-95/мес

## Текущие расходы (факт)
- 1 нода BitLaunch Amsterdam: $22/мес
- Баланс BitLaunch: $24.96

## Доход (при 200 юзерах)
- 200 × 149₽ = 29 800₽/мес (~$320)
- Маржа: ~85-90%
- Себестоимость 1 юзера: ~28-35₽
- Окупаемость: с ~42 юзеров

---

# ЧАСТЬ 9. ПЛАН ДЕПЛОЯ (14 дней)

## Дни 1-2: Серверная инфраструктура [В ПРОЦЕССЕ]
- [x] Аренда первого сервера (BitLaunch Amsterdam, 168.100.11.140)
- [x] SSH-ключ создан и добавлен
- [ ] Подключиться по SSH и установить Remnawave
- [ ] Купить второй сервер в другой локации

## Дни 3-4: Установка стека
- [ ] XRay нода + Beszel + Reshala на VPN-сервере
- [ ] Подобрать правильный SNI через RealiTLScanner
- [ ] Настроить remna-shop (Telegram-бот)
- [ ] Тест подключения из России

## Дни 5-6: Подписки и API
- [ ] Настроить subscription endpoint для Happ
- [ ] Тест автообновления и автоподключения
- [ ] MTProto proxy

## Дни 7-10: Биллинг + второй уровень
- [ ] Крипто-оплата в боте
- [ ] Российский relay (уровень 2)
- [ ] Сайт-прикрытие на relay

## Дни 11-14: Smart Balancer + тесты
- [ ] API мониторинг всех нод
- [ ] Автоматическая ротация в subscription
- [ ] Алерты в Telegram
- [ ] Полное тестирование из РФ

---

# ЧАСТЬ 10. СОЗДАННЫЕ ФАЙЛЫ

- /mnt/user-data/outputs/deploy-vless.sh — скрипт деплоя XRay VLESS Reality (УСТАРЕЛ — заменяется на Remnawave)
- /mnt/user-data/outputs/README-VLESS.md — инструкция к скрипту (УСТАРЕЛ)
- /mnt/user-data/outputs/ARCHITECTURE.md — полный архитектурный документ
- Geph4 клиент: разобран в /home/claude/geph/geph4-client-master/

---

# ЧАСТЬ 11. КЛЮЧЕВЫЕ ССЫЛКИ

## Стек
- Remnawave: https://docs.rw/
- Beszel: https://beszel.dev/
- Reshala: https://github.com/DonMatteoVPN/Reshala-Remnawave-Bedolaga
- remna-shop: https://github.com/catoo-hub/remna-shop
- Happ документация: https://www.happ.su/main/dev-docs/app-management

## Белые списки
- https://github.com/hxehex/russia-mobile-internet-whitelist
- https://github.com/VasiliyBP/rmi-whitelist
- https://github.com/igareck/vpn-configs-for-russia

## Гайды
- VLESS Reality настройка: https://github.com/XTLS/Xray-core/discussions/3518
- Обход белых списков через chain: https://habr.com/en/articles/990206/
- Как ТСПУ ловит VLESS: https://habr.com/ru/articles/1009542/
- Multi-hop VPN цепочка: https://habr.com/ru/articles/926786/

## Текущий сервер
- BitLaunch панель: https://app.bitlaunch.io/
- Сервер: 168.100.11.140 (Amsterdam, Ubuntu 22.04, 2CPU/2GB)
