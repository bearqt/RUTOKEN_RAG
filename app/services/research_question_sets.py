from __future__ import annotations

from app.services.benchmark_seed_data import get_seed_question_sets


RESEARCH_SET_ID = "research-scrape-result-25-typed"
RESEARCH_SET_NAME = "Research scrape_result_25 / typed questions"
RESEARCH_BM25_CHALLENGE_SET_ID = "research-scrape-result-25-bm25-challenge"
RESEARCH_BM25_CHALLENGE_SET_NAME = "Research scrape_result_25 / BM25 challenge"
RESEARCH_BM25_STRESS_SET_ID = "research-scrape-result-25-bm25-stress"
RESEARCH_BM25_STRESS_SET_NAME = "Research scrape_result_25 / BM25 stress"
RESEARCH_BM25_NATURAL_SET_ID = "research-scrape-result-25-bm25-natural"
RESEARCH_BM25_NATURAL_SET_NAME = "Research scrape_result_25 / BM25 natural stress"


PAGE_TITLES = {
    "196673783": "Настройка модуля интеграции с кластером PostgreSQL",
    "199655433": "Электронная цифровая подпись и шифрование в почтовом клиенте Evolution",
    "201850922": "Использование Рутокен OTP для защиты аккаунта в общедоступных сервисах",
    "204832808": "ЦУР для GNU/Linux. О программе",
    "204832814": "ЦУР для GNU/Linux. Подключение устройств Рутокен",
    "206438439": "ЦУР для Windows. О программе",
    "206438545": "ЦУР для Windows. Подключение устройства Рутокен",
    "207880233": "Обзорная информация о считывателях Рутокен",
    "206438702": "Работа со смарт-картой Рутокен в ОС семейства GNU/Linux",
    "206438917": "Матрица мобильных партнерских решений с устройством Рутокен 3.0 NFC",
    "209748081": "Подписание при помощи утилиты osslsigncode",
    "214302735": "КриптоПро CSP 5.0 R3",
    "215842829": "Функции для работы с объектами",
    "215842836": "Функции создания подписи",
    "215842840": "Функции проверки подписи",
    "215842842": "Функции для работы с ключами",
    "217251842": "Модуль загрузки ключевой информации Рутокен",
    "217252090": "Компоненты (версия 7.1)",
    "217252091": "Лицензирование (версия 7.1)",
    "217252097": "Серверные компоненты (версия 7.1)",
    "217252099": "Сетевое взаимодействие (версия 7.1)",
    "217252102": "Порядок установки (версия 7.1)",
    "217252105": "LDAP (версия 7.1)",
    "217252113": "Сервисные сертификаты (версия 7.1)",
    "217252127": "PostgreSQL и Postgres Pro (версия 7.1)",
}


EXISTING_CASES_BY_TYPE = {
    "factoid": [
        "otp-totp-algorithm",
        "cur-linux-supported-devices",
        "cur-windows-supported-os",
        "reader-overview-scr3001-protocols",
        "mobile-matrix-platforms",
        "osslsigncode-example-os",
        "keybox-license-types",
        "keybox-network-postgresql-port",
    ],
    "exact_match": [
        "pkcs11-destroy-object",
        "pkcs11-sign-init",
        "pkcs11-verify-init",
        "pkcs11-generate-keypair",
        "osslsigncode-install-command",
        "osslsigncode-keygen-command",
        "keybox-postgres-storage-script",
        "keybox-postgres-pghba-template",
    ],
    "comparison": [
        "reader-overview-contact-vs-nfc",
        "cur-windows-modes",
        "cur-linux-modes",
        "cryptopro-csp-three-modes",
        "keybox-server-web-servers",
        "keybox-license-counting-user-based",
        "cur-linux-connect-smart-card",
        "cur-windows-connect-smart-card",
    ],
    "integration": [
        "pg-cluster-module-purpose",
        "otp-public-services-prerequisites",
        "smartcard-linux-prerequisites",
        "osslsigncode-integration-modules",
        "keybox-install-order-linux",
        "keybox-ldap-supported-services",
        "keybox-service-cert-oidc",
        "keybox-server-dotnet-and-urlrewrite",
    ],
    "multi-hop": [
        "pg-cluster-module-prerequisites",
        "evolution-protected-mail-topics",
        "key-loader-main-sections",
        "keybox-components-categories",
        "keybox-additional-modules",
        "keybox-environment-user-directories",
        "keybox-service-cert-requirements",
        "keybox-server-components-linux-mandatory",
    ],
}


ROUTING_CASES = [
    {
        "case_key": "routing-postgresql-cluster-module-doc",
        "question": "В какой инструкции документации Rutoken KeyBox описан модуль интеграции с кластером PostgreSQL?",
        "required_sources": ["https://dev.rutoken.ru/pages/viewpage.action?pageId=196673783"],
        "reference_answer": PAGE_TITLES["196673783"],
        "tags": ["research25", "routing", "page_196673783"],
        "notes": "Маршрутизация к документу по интеграции с кластером PostgreSQL.",
    },
    {
        "case_key": "routing-evolution-mail-doc",
        "question": "В каком документе рассматриваются задачи электронной подписи и шифрования для почтового клиента Evolution?",
        "required_sources": ["https://dev.rutoken.ru/pages/viewpage.action?pageId=199655433"],
        "reference_answer": PAGE_TITLES["199655433"],
        "tags": ["research25", "routing", "page_199655433"],
        "notes": "Маршрутизация к how-to документу по Evolution.",
    },
    {
        "case_key": "routing-cur-linux-os-doc",
        "question": "В каком документе ЦУР для GNU/Linux перечислены поддерживаемые семейства дистрибутивов и операционных систем?",
        "required_sources": ["https://dev.rutoken.ru/pages/viewpage.action?pageId=204832808"],
        "reference_answer": PAGE_TITLES["204832808"],
        "tags": ["research25", "routing", "page_204832808"],
        "notes": "Маршрутизация к обзорной странице ЦУР для GNU/Linux.",
    },
    {
        "case_key": "routing-cur-windows-connect-doc",
        "question": "В какой инструкции ЦУР для Windows описаны варианты подключения устройства Рутокен, включая NFC?",
        "required_sources": ["https://dev.rutoken.ru/pages/viewpage.action?pageId=206438545"],
        "reference_answer": PAGE_TITLES["206438545"],
        "tags": ["research25", "routing", "page_206438545"],
        "notes": "Маршрутизация к документу про подключение устройств в Windows.",
    },
    {
        "case_key": "routing-reader-comparison-doc",
        "question": "В каком документе документации сравниваются считыватели Rutoken SCR 3001 и SCR 3101 NFC?",
        "required_sources": ["https://dev.rutoken.ru/pages/viewpage.action?pageId=207880233"],
        "reference_answer": PAGE_TITLES["207880233"],
        "tags": ["research25", "routing", "page_207880233"],
        "notes": "Маршрутизация к обзорному документу по считывателям.",
    },
    {
        "case_key": "routing-osslsigncode-keygen-doc",
        "question": "В какой инструкции приведен пример команды генерации RSA-ключевой пары через pkcs11-tool для сценария с osslsigncode?",
        "required_sources": ["https://dev.rutoken.ru/pages/viewpage.action?pageId=209748081"],
        "reference_answer": PAGE_TITLES["209748081"],
        "tags": ["research25", "routing", "page_209748081"],
        "notes": "Маршрутизация к инструкции по osslsigncode.",
    },
    {
        "case_key": "routing-pkcs11-destroy-object-doc",
        "question": "В каком разделе PKCS#11 документации описана функция удаления объекта C_DestroyObject()?",
        "required_sources": ["https://dev.rutoken.ru/pages/viewpage.action?pageId=215842829"],
        "reference_answer": PAGE_TITLES["215842829"],
        "tags": ["research25", "routing", "page_215842829"],
        "notes": "Маршрутизация к reference-документу по операциям с объектами.",
    },
    {
        "case_key": "routing-keybox-pghba-doc",
        "question": "В каком документе Rutoken KeyBox 7.1 приведен шаблон строки для настройки удаленного доступа в pg_hba.conf?",
        "required_sources": ["https://dev.rutoken.ru/pages/viewpage.action?pageId=217252127"],
        "reference_answer": PAGE_TITLES["217252127"],
        "tags": ["research25", "routing", "page_217252127"],
        "notes": "Маршрутизация к инфраструктурному документу по PostgreSQL/Postgres Pro.",
    },
]


BM25_CHALLENGE_CASES = [
    {
        "base_case_key": "pg-cluster-module-purpose",
        "question": "Какой компонент KeyBox нужен, если хранилище системы должно оставаться доступным при отказе отдельного узла БД?",
        "bucket": "bm25_unfriendly",
        "notes": "Парафраз без точного повтора формулировки про модуль интеграции и отказоустойчивый кластер.",
    },
    {
        "base_case_key": "evolution-protected-mail-topics",
        "question": "Какой набор действий с письмами покрывает инструкция для пользователей Evolution, если нужна не просто отправка, а защита содержимого и подтверждение авторства?",
        "bucket": "bm25_unfriendly",
        "notes": "Суммаризация без прямого повтора терминов из заголовка документа.",
    },
    {
        "base_case_key": "otp-totp-algorithm",
        "question": "Какой алгоритм одноразовых паролей реализован в Рутокен OTP?",
        "bucket": "control",
        "notes": "Контрольный BM25-friendly factoid.",
    },
    {
        "base_case_key": "cur-linux-supported-os",
        "question": "Для каких классов Linux-платформ рассчитан ЦУР, если смотреть не на один дистрибутив, а на семейства поддерживаемых систем?",
        "bucket": "bm25_unfriendly",
        "notes": "Парафраз с абстракцией над списком дистрибутивов.",
    },
    {
        "base_case_key": "cur-linux-connect-smart-card",
        "question": "Какими способами в Linux можно подключить смарт-карту к ЦУР, если учитывать и физический контакт, и беспроводной сценарий?",
        "bucket": "bm25_unfriendly",
        "notes": "Сравнительная формулировка вместо точного перечисления интерфейсов.",
    },
    {
        "base_case_key": "cur-windows-modes",
        "question": "Какие действия появляются только в административном сценарии работы ЦУР под Windows и не относятся к обычному пользовательскому режиму?",
        "bucket": "bm25_unfriendly",
        "notes": "Сравнение режимов с низким лексическим пересечением с исходной формулировкой.",
    },
    {
        "base_case_key": "cur-windows-connect-smart-card",
        "question": "Какие каналы подключения носителей поддерживает Windows-версия ЦУР для токенов и карт Рутокен?",
        "bucket": "bm25_unfriendly",
        "notes": "Обобщенная формулировка без прямого повтора текста про USB и NFC.",
    },
    {
        "base_case_key": "reader-overview-contact-vs-nfc",
        "question": "Как различается назначение двух ридеров линейки SCR, если один рассчитан только на карту с контактами, а другой работает и с радиоинтерфейсом?",
        "bucket": "bm25_unfriendly",
        "notes": "Сравнение по функциям без явного повторения имен моделей в самом вопросе.",
    },
    {
        "base_case_key": "smartcard-linux-prerequisites",
        "question": "Какие проверки окружения и какие программные компоненты нужно обеспечить до начала работы со смарт-картой в Linux?",
        "bucket": "bm25_unfriendly",
        "notes": "Интеграционный вопрос на подготовительные шаги.",
    },
    {
        "base_case_key": "mobile-matrix-platforms",
        "question": "Какие мобильные платформы чаще всего фигурируют в матрице партнерских решений для Рутокен 3.0 NFC?",
        "bucket": "control",
        "notes": "Контрольный BM25-friendly фактологический вопрос.",
    },
    {
        "base_case_key": "osslsigncode-keygen-command",
        "question": "Как выглядит пример инициализации ключевой пары на токене для сценария подписи через osslsigncode?",
        "bucket": "bm25_unfriendly",
        "notes": "Парафраз exact-match вопроса в сценарную формулировку.",
    },
    {
        "base_case_key": "cryptopro-csp-three-modes",
        "question": "Какие три модели хранения и использования ключевого материала рассматриваются для работы Рутокен с КриптоПро CSP 5.0 R3?",
        "bucket": "bm25_unfriendly",
        "notes": "Сравнение трех вариантов без дословного повтора ответа.",
    },
    {
        "base_case_key": "pkcs11-destroy-object",
        "question": "Какая функция PKCS#11 используется для удаления объекта?",
        "bucket": "control",
        "notes": "Контрольный exact-match кейс.",
    },
    {
        "base_case_key": "pkcs11-sign-init",
        "question": "Какой PKCS#11 вызов используется для инициализации операции подписи?",
        "bucket": "control",
        "notes": "Контрольный exact-match кейс.",
    },
    {
        "base_case_key": "pkcs11-verify-init",
        "question": "Какой PKCS#11 вызов инициализирует операцию проверки подписи?",
        "bucket": "control",
        "notes": "Контрольный exact-match кейс.",
    },
    {
        "base_case_key": "pkcs11-generate-keypair",
        "question": "Какая функция PKCS#11 используется для генерации пары ключей?",
        "bucket": "control",
        "notes": "Контрольный exact-match кейс.",
    },
    {
        "base_case_key": "key-loader-main-sections",
        "question": "Какие смысловые разделы образуют структуру руководства по модулю загрузки ключевой информации, если смотреть на него как на документ про функции, состав АРМ и правила применения?",
        "bucket": "bm25_unfriendly",
        "notes": "Суммаризация структуры документа.",
    },
    {
        "base_case_key": "keybox-components-categories",
        "question": "Как в документации 7.1 укрупненно разложены части системы и какие варианты серверного хранилища данных при этом упоминаются?",
        "bucket": "bm25_unfriendly",
        "notes": "Multi-hop вопрос: группы компонентов плюс хранилища данных.",
    },
    {
        "base_case_key": "keybox-license-types",
        "question": "Как устроено деление лицензирования в KeyBox 7.1, если отделить базовое право на систему от возможностей, которые приобретаются отдельно?",
        "bucket": "bm25_unfriendly",
        "notes": "Парафраз, скрывающий явные термины ответа.",
    },
    {
        "base_case_key": "keybox-server-web-servers",
        "question": "Какие веб-серверные роли поддерживаются для серверной части KeyBox на Windows и Linux, включая проксирующую схему публикации?",
        "bucket": "bm25_unfriendly",
        "notes": "Сравнение платформ и reverse-proxy сценария.",
    },
    {
        "base_case_key": "keybox-network-postgresql-port",
        "question": "Какой номер сетевого соединения отведен PostgreSQL в схеме взаимодействия компонентов KeyBox 7.1?",
        "bucket": "bm25_unfriendly",
        "notes": "Парафраз без прямого слова порт.",
    },
    {
        "base_case_key": "keybox-install-order-linux",
        "question": "Какие классы подготовительных работ предшествуют установке KeyBox 7.1 на Linux, если смотреть на инфраструктуру, сертификаты и последующую конфигурацию?",
        "bucket": "bm25_unfriendly",
        "notes": "Суммаризация этапа подготовки окружения.",
    },
    {
        "base_case_key": "keybox-ldap-supported-services",
        "question": "С какими типами корпоративных каталогов умеет интегрироваться KeyBox 7.1 через LDAP?",
        "bucket": "bm25_unfriendly",
        "notes": "Парафраз с заменой словосочетания LDAP-службы на корпоративные каталоги.",
    },
    {
        "base_case_key": "keybox-service-cert-requirements",
        "question": "Какие ограничения накладываются на TLS-сертификат узла, чтобы его можно было использовать на сервере KeyBox?",
        "bucket": "bm25_unfriendly",
        "notes": "Парафраз требований к Subject/SAN/EKU без дословного повтора.",
    },
    {
        "base_case_key": "keybox-postgres-storage-script",
        "question": "Как называется SQL-файл инициализации, которым заполняют PostgreSQL-хранилище для KeyBox 7.1?",
        "bucket": "bm25_unfriendly",
        "notes": "Парафраз вопроса про конкретный SQL-скрипт.",
    },
]


BM25_STRESS_CASES = [
    {
        "base_case_key": "pg-cluster-module-purpose",
        "question": "Какой механизм высокой доступности хранилища предлагают подключить, чтобы система переживала отказ отдельной машины с базой данных?",
        "bucket": "bm25_unfriendly",
        "notes": "Очень косвенная формулировка без названия модуля и продукта.",
    },
    {
        "base_case_key": "evolution-protected-mail-topics",
        "question": "Какой сценарий защищенного обмена письмами разбирается в инструкции для настольного клиента: подтверждение автора, сокрытие содержимого и отправка такого сообщения?",
        "bucket": "bm25_unfriendly",
        "notes": "Косвенное описание EDS/шифрования без имени клиента.",
    },
    {
        "base_case_key": "otp-totp-algorithm",
        "question": "Какой способ вычисления одноразового кода здесь привязан к текущему моменту времени, а не к счетчику событий?",
        "bucket": "bm25_unfriendly",
        "notes": "Убран явный якорь OTP/TOTP из запроса.",
    },
    {
        "base_case_key": "cur-linux-supported-os",
        "question": "На какие ветви Linux-экосистемы рассчитан этот инструмент администрирования, если смотреть на семейства пакетов и примеры дистрибутивов?",
        "bucket": "bm25_unfriendly",
        "notes": "Абстракция над списком ОС и дистрибутивов.",
    },
    {
        "base_case_key": "cur-linux-connect-smart-card",
        "question": "Какими двумя физическими способами здесь предлагают работать с картой на рабочем месте: через слот и через поднесение?",
        "bucket": "bm25_unfriendly",
        "notes": "Убраны Linux, ЦУР и явные названия интерфейсов.",
    },
    {
        "base_case_key": "cur-windows-modes",
        "question": "В каком варианте работы появляются операции администратора носителя, а в каком остаются только обычные пользовательские действия?",
        "bucket": "bm25_unfriendly",
        "notes": "Сильный парафраз сравнения режимов.",
    },
    {
        "base_case_key": "cur-windows-connect-smart-card",
        "question": "Какие типы носителей и способы их присоединения рассматриваются в настольном сценарии, если учитывать брелок, карту и поднесение к антенне?",
        "bucket": "bm25_unfriendly",
        "notes": "Косвенная формулировка Windows-кейса.",
    },
    {
        "base_case_key": "reader-overview-contact-vs-nfc",
        "question": "Как различаются две модели ридеров, если одна работает только с контактной картой, а другая рассчитана на радиоинтерфейс?",
        "bucket": "bm25_unfriendly",
        "notes": "Сравнение без явных имен моделей.",
    },
    {
        "base_case_key": "smartcard-linux-prerequisites",
        "question": "Что нужно обеспечить в системе заранее: видимость ридера, набор библиотек и доступ к нужному криптографическому модулю?",
        "bucket": "bm25_unfriendly",
        "notes": "Подготовительные шаги без прямого названия Linux/PKCS#11.",
    },
    {
        "base_case_key": "mobile-matrix-platforms",
        "question": "Какие мобильные ОС доминируют среди совместимых партнерских решений для NFC-носителя третьего поколения?",
        "bucket": "bm25_unfriendly",
        "notes": "Убрано точное имя матрицы и продукта.",
    },
    {
        "base_case_key": "osslsigncode-keygen-command",
        "question": "Какая демонстрационная строка запуска используется перед подписанием, чтобы выпустить RSA-пару прямо на носителе через утилиту PKCS#11?",
        "bucket": "bm25_unfriendly",
        "notes": "Сценарная формулировка вместо прямого exact-match вопроса.",
    },
    {
        "base_case_key": "cryptopro-csp-three-modes",
        "question": "Какие три схемы обращения к ключевому материалу описаны для связки носителя с CSP: прямой вызов, защищенный обмен с ядром и хранение в собственной защищенной области?",
        "bucket": "bm25_unfriendly",
        "notes": "Смысловой парафраз трех режимов.",
    },
    {
        "base_case_key": "pkcs11-destroy-object",
        "question": "Как называется API-вызов, который стирает уже созданную сущность из криптографического хранилища?",
        "bucket": "bm25_unfriendly",
        "notes": "Убраны слова PKCS#11 и объект.",
    },
    {
        "base_case_key": "pkcs11-sign-init",
        "question": "Какой вызов подготавливает механизм подписания до фактического вычисления подписи?",
        "bucket": "bm25_unfriendly",
        "notes": "Косвенная формулировка без точного названия операции.",
    },
    {
        "base_case_key": "pkcs11-verify-init",
        "question": "Какой вызов подготавливает механизм проверки подписи еще до запуска самой верификации?",
        "bucket": "bm25_unfriendly",
        "notes": "Парафраз verify-init без PKCS#11.",
    },
    {
        "base_case_key": "pkcs11-generate-keypair",
        "question": "Какой вызов отвечает за выпуск сразу двух связанных ключей в криптографическом API?",
        "bucket": "bm25_unfriendly",
        "notes": "Убраны слова PKCS#11 и пара ключей.",
    },
    {
        "base_case_key": "key-loader-main-sections",
        "question": "Если смотреть на руководство по загрузке ключей как на структуру документа, какие три смысловые части в нем выделены?",
        "bucket": "bm25_unfriendly",
        "notes": "Суммаризация структуры руководства.",
    },
    {
        "base_case_key": "keybox-components-categories",
        "question": "Как на верхнем уровне устроена система: какие классы ее модулей выделены и какие серверы данных допускаются как место хранения?",
        "bucket": "bm25_unfriendly",
        "notes": "Multi-hop: компоненты плюс поддерживаемые СУБД.",
    },
    {
        "base_case_key": "keybox-license-types",
        "question": "Как разделены права использования продукта, если отделить базовую поставку от возможностей, которые приобретаются отдельно?",
        "bucket": "bm25_unfriendly",
        "notes": "Убран якорь лицензия/модуль из первой половины вопроса.",
    },
    {
        "base_case_key": "keybox-server-web-servers",
        "question": "Какие роли веб-публикации допустимы для серверной части на разных ОС, если один вариант нативен для Windows, а два других используются как прокси?",
        "bucket": "bm25_unfriendly",
        "notes": "Косвенное сравнение IIS/Nginx/Apache.",
    },
    {
        "base_case_key": "keybox-network-postgresql-port",
        "question": "Какой номер соединения отведен серверу данных в схеме обмена между компонентами?",
        "bucket": "bm25_unfriendly",
        "notes": "Убраны слова порт, PostgreSQL и KeyBox.",
    },
    {
        "base_case_key": "keybox-install-order-linux",
        "question": "Из каких крупных подготовительных шагов состоит внедрение системы под Linux до момента работы с прикладными модулями?",
        "bucket": "bm25_unfriendly",
        "notes": "Очень общий multi-step вопрос.",
    },
    {
        "base_case_key": "keybox-ldap-supported-services",
        "question": "С какими каталогами учетных записей умеет интегрироваться эта система через LDAP?",
        "bucket": "bm25_unfriendly",
        "notes": "Заменены LDAP-службы на корпоративные каталоги.",
    },
    {
        "base_case_key": "keybox-service-cert-requirements",
        "question": "Что должно быть отражено в имени узла и расширениях сертификата, чтобы его допустили для серверной роли?",
        "bucket": "bm25_unfriendly",
        "notes": "Косвенный вопрос про Subject/SAN/EKU.",
    },
    {
        "base_case_key": "keybox-postgres-storage-script",
        "question": "Как называется SQL-файл инициализации, которым поднимают схему хранилища для варианта на PostgreSQL?",
        "bucket": "bm25_unfriendly",
        "notes": "Косвенная формулировка вопроса про скрипт.",
    },
]


BM25_NATURAL_CASES = [
    {
        "base_case_key": "pg-cluster-module-purpose",
        "question": "Как сделать так, чтобы KeyBox не зависел от одной ноды PostgreSQL?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественный вопрос про отказоустойчивость без названия модуля.",
    },
    {
        "base_case_key": "evolution-protected-mail-topics",
        "question": "Что вообще можно сделать с безопасной почтой в этом настольном клиенте?",
        "bucket": "bm25_unfriendly",
        "notes": "Короткий пользовательский вопрос вместо перечисления терминов из документа.",
    },
    {
        "base_case_key": "otp-totp-algorithm",
        "question": "Этот одноразовый код зависит от времени или от счетчика?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественный вопрос без прямого якоря TOTP.",
    },
    {
        "base_case_key": "cur-linux-supported-os",
        "question": "На каких Linux-системах вообще должен работать ЦУР?",
        "bucket": "bm25_unfriendly",
        "notes": "Пользовательская формулировка вместо точного перечисления семейств ОС.",
    },
    {
        "base_case_key": "cur-linux-connect-smart-card",
        "question": "Как подключить смарт-карту к ЦУР в Linux?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественный короткий вопрос про варианты подключения.",
    },
    {
        "base_case_key": "cur-windows-modes",
        "question": "Что меняется в режиме администратора в ЦУР для Windows?",
        "bucket": "bm25_unfriendly",
        "notes": "Живая формулировка без точного повтора ответа.",
    },
    {
        "base_case_key": "cur-windows-connect-smart-card",
        "question": "Как в Windows подключать разные носители Рутокен к ЦУР?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественный вопрос без явного перечисления USB, контактного интерфейса и NFC.",
    },
    {
        "base_case_key": "reader-overview-contact-vs-nfc",
        "question": "Чем отличается обычный ридер от NFC-ридера Рутокен?",
        "bucket": "bm25_unfriendly",
        "notes": "Простой естественный вопрос без точных имен моделей.",
    },
    {
        "base_case_key": "smartcard-linux-prerequisites",
        "question": "Что нужно проверить в Linux, если смарт-карта сразу не заводится?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественная постановка про prerequisites.",
    },
    {
        "base_case_key": "mobile-matrix-platforms",
        "question": "На каких мобильных ОС чаще всего работают такие решения?",
        "bucket": "bm25_unfriendly",
        "notes": "Короткий пользовательский вопрос вместо формулировки про матрицу.",
    },
    {
        "base_case_key": "osslsigncode-keygen-command",
        "question": "Какой командой на токене создают RSA-ключи для сценария с osslsigncode?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественный вопрос с меньшим лексическим совпадением с точным ответом.",
    },
    {
        "base_case_key": "cryptopro-csp-three-modes",
        "question": "Какие вообще есть сценарии работы носителя с CSP?",
        "bucket": "bm25_unfriendly",
        "notes": "Простой разговорный вопрос вместо точного сравнения трех режимов.",
    },
    {
        "base_case_key": "pkcs11-destroy-object",
        "question": "Как в PKCS#11 удалить объект?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественный короткий вопрос без упоминания названия функции.",
    },
    {
        "base_case_key": "pkcs11-sign-init",
        "question": "Каким вызовом в PKCS#11 запускают подготовку к подписи?",
        "bucket": "bm25_unfriendly",
        "notes": "Похоже на реальный вопрос разработчика, но без точного имени функции.",
    },
    {
        "base_case_key": "pkcs11-verify-init",
        "question": "Каким вызовом в PKCS#11 начинают проверку подписи?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественный вопрос без точного совпадения с названием функции.",
    },
    {
        "base_case_key": "pkcs11-generate-keypair",
        "question": "Каким вызовом в PKCS#11 генерируют сразу пару ключей?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественный вопрос разработчика.",
    },
    {
        "base_case_key": "key-loader-main-sections",
        "question": "Из каких основных частей состоит руководство по модулю загрузки ключей?",
        "bucket": "bm25_unfriendly",
        "notes": "Короткий вопрос про структуру документа.",
    },
    {
        "base_case_key": "keybox-components-categories",
        "question": "Как вообще устроен KeyBox 7.1 по крупным компонентам и хранилищам данных?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественный multi-hop вопрос.",
    },
    {
        "base_case_key": "keybox-license-types",
        "question": "Какие виды лицензий вообще нужны для этой системы?",
        "bucket": "bm25_unfriendly",
        "notes": "Очень естественный вопрос, но без точной структуры ответа.",
    },
    {
        "base_case_key": "keybox-server-web-servers",
        "question": "Через какие веб-серверы можно опубликовать KeyBox?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественная пользовательская формулировка вместо точного списка.",
    },
    {
        "base_case_key": "keybox-network-postgresql-port",
        "question": "На какой порт должна ходить система к своей базе данных?",
        "bucket": "bm25_unfriendly",
        "notes": "Простой вопрос, но с меньшим совпадением со схемой сетевого взаимодействия.",
    },
    {
        "base_case_key": "keybox-install-order-linux",
        "question": "Что нужно сделать перед установкой KeyBox 7.1 на Linux?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественный вопрос про этап подготовки.",
    },
    {
        "base_case_key": "keybox-ldap-supported-services",
        "question": "С какими каталогами пользователей она умеет работать по LDAP?",
        "bucket": "bm25_unfriendly",
        "notes": "Пользовательская формулировка вместо официального термина LDAP-службы.",
    },
    {
        "base_case_key": "keybox-service-cert-requirements",
        "question": "Что должно быть в сертификате, который ставят на сервер?",
        "bucket": "bm25_unfriendly",
        "notes": "Естественный вопрос без Subject/SAN/EKU в запросе.",
    },
    {
        "base_case_key": "keybox-postgres-storage-script",
        "question": "Какой SQL-файл нужен, чтобы подготовить схему БД для этой системы?",
        "bucket": "bm25_unfriendly",
        "notes": "Короткий прикладной вопрос вместо точного совпадения с ответом.",
    },
]


def get_research_question_sets() -> list[dict]:
    return [
        get_research_scrape_result_25_question_set(),
        get_research_scrape_result_25_bm25_challenge_set(),
        get_research_scrape_result_25_bm25_stress_set(),
        get_research_scrape_result_25_bm25_natural_set(),
    ]


def get_research_scrape_result_25_question_set() -> dict:
    question_by_key = {}
    for payload in get_seed_question_sets():
        for question in payload["questions"]:
            question_by_key[question["case_key"]] = question

    questions: list[dict] = []
    for question_type, case_keys in EXISTING_CASES_BY_TYPE.items():
        for case_key in case_keys:
            base = dict(question_by_key[case_key])
            page_tag = _page_tag(base.get("required_sources", []))
            tags = list(base.get("tags", []))
            tags.extend(["research25", question_type, page_tag])
            base["tags"] = _unique(tags)
            questions.append(base)

    questions.extend(ROUTING_CASES)
    return {
        "id": RESEARCH_SET_ID,
        "name": RESEARCH_SET_NAME,
        "description": (
            "48 вопросов по 25 документам корпуса scrape_result_25, разбитых по типам: "
            "factoid, exact_match, routing, comparison, integration, multi-hop."
        ),
        "questions": questions,
    }


def get_research_scrape_result_25_bm25_challenge_set() -> dict:
    question_by_key = {}
    for payload in get_seed_question_sets():
        for question in payload["questions"]:
            question_by_key[question["case_key"]] = question

    questions: list[dict] = []
    for item in BM25_CHALLENGE_CASES:
        base = dict(question_by_key[item["base_case_key"]])
        page_tag = _page_tag(base.get("required_sources", []))
        tags = list(base.get("tags", []))
        tags.extend(["research25", "bm25_challenge", item["bucket"], page_tag])
        base["question"] = item["question"]
        base["tags"] = _unique(tags)
        base["notes"] = item["notes"]
        questions.append(base)

    return {
        "id": RESEARCH_BM25_CHALLENGE_SET_ID,
        "name": RESEARCH_BM25_CHALLENGE_SET_NAME,
        "description": (
            "25 вопросов по тем же 25 документам scrape_result_25. "
            "Из них 19 вопросов специально переформулированы как bm25_unfriendly "
            "через парафраз, сравнение, multi-hop и summary-постановки; "
            "6 вопросов оставлены как control."
        ),
        "questions": questions,
    }


def get_research_scrape_result_25_bm25_stress_set() -> dict:
    question_by_key = {}
    for payload in get_seed_question_sets():
        for question in payload["questions"]:
            question_by_key[question["case_key"]] = question

    questions: list[dict] = []
    for item in BM25_STRESS_CASES:
        base = dict(question_by_key[item["base_case_key"]])
        page_tag = _page_tag(base.get("required_sources", []))
        tags = list(base.get("tags", []))
        tags.extend(["research25", "bm25_stress", item["bucket"], page_tag])
        base["question"] = item["question"]
        base["tags"] = _unique(tags)
        base["notes"] = item["notes"]
        questions.append(base)

    return {
        "id": RESEARCH_BM25_STRESS_SET_ID,
        "name": RESEARCH_BM25_STRESS_SET_NAME,
        "description": (
            "25 вопросов по тем же 25 документам scrape_result_25. "
            "Все вопросы агрессивно переформулированы через косвенные описания, "
            "сценарные постановки и multi-hop формулировки, чтобы быть максимально "
            "неудобными для чистого BM25."
        ),
        "questions": questions,
    }


def get_research_scrape_result_25_bm25_natural_set() -> dict:
    question_by_key = {}
    for payload in get_seed_question_sets():
        for question in payload["questions"]:
            question_by_key[question["case_key"]] = question

    questions: list[dict] = []
    for item in BM25_NATURAL_CASES:
        base = dict(question_by_key[item["base_case_key"]])
        page_tag = _page_tag(base.get("required_sources", []))
        tags = list(base.get("tags", []))
        tags.extend(["research25", "bm25_natural", item["bucket"], page_tag])
        base["question"] = item["question"]
        base["tags"] = _unique(tags)
        base["notes"] = item["notes"]
        questions.append(base)

    return {
        "id": RESEARCH_BM25_NATURAL_SET_ID,
        "name": RESEARCH_BM25_NATURAL_SET_NAME,
        "description": (
            "25 вопросов по тем же 25 документам scrape_result_25. "
            "Вопросы сформулированы максимально естественно и близко к реальным "
            "пользовательским запросам, но без сильного лексического совпадения "
            "с формулировками в документации."
        ),
        "questions": questions,
    }


def _page_tag(required_sources: list[str]) -> str:
    for source in required_sources:
        if "pageId=" not in source:
            continue
        page_id = source.rsplit("pageId=", 1)[-1]
        if page_id.isdigit():
            return f"page_{page_id}"
    return "page_unknown"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
