from __future__ import annotations

from app.services.benchmark_seed_data import get_seed_question_sets


RESEARCH_SET_ID = "research-scrape-result-25-typed"
RESEARCH_SET_NAME = "Research scrape_result_25 / typed questions"


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


def get_research_question_sets() -> list[dict]:
    return [get_research_scrape_result_25_question_set()]


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
