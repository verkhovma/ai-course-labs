# -*- coding: utf-8 -*-
"""
Модуль для работы с GigaChat API
Лабораторная работа No1
Дисциплина: Искусственный интеллект
Автор: [Верхов Михаил Алексеевич]
Группа: [ФИТ-221]
Дата: 2026.03.28
"""
import os
import sys
import logging
from typing import Dict, Optional
from datetime import datetime
import requests
from uuid import uuid4
import json
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



class GigaChatClient:
    """
    Клиент для взаимодействия с GigaChat API.
    Атрибуты:
    GIGACHAT_AUTHORIZATION_KEY (str): Ключ для аутентификации
    url_auth (str): URL аутентификации
    access_token (str): токен доступа сессии
    url_models (str): URL списка моделей
    model_name (str): Название используемой модели
    url_api (str): URL API endpoint
    cert_filename (str): Имя (путь) файла сертификата минцифры .crt
    """


    def __init__(self, GIGACHAT_AUTHORIZATION_KEY: str):
        """
        Инициализация клиента GigaChat.
        Args:
        GIGACHAT_AUTHORIZATION_KEY: Ключ аутентификации
        Raises:
        ValueError: Если токен не передан
        """
        if not GIGACHAT_AUTHORIZATION_KEY:
            raise ValueError("Необходимо указать GIGACHAT_AUTHORIZATION_KEY")
        self.GIGACHAT_AUTHORIZATION_KEY = GIGACHAT_AUTHORIZATION_KEY
        self.url_auth = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        self.access_token = None
        self.url_models = "https://gigachat.devices.sberbank.ru/api/v1/models"
        self.model_name = "GigaChat"
        self.url_api = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        # у Сбера сертификат минцифры
        self.cert_filename = "russian_trusted_root_ca_pem.crt"
        logger.info(f"Клиент инициализирован. model: {self.model_name}")


    def auth(self) -> None:
        """
        Получение токена доступа (Токен доступа действителен в течение 30 минут,
        Запросы на получение токена можно отправлять до 10 раз в секунду)
        """
        payload={'scope': 'GIGACHAT_API_PERS'}
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': str(uuid4()),
            'Authorization': f'Basic {self.GIGACHAT_AUTHORIZATION_KEY}'
        }
        response = requests.post(self.url_auth, headers=headers, data=payload, timeout=30, verify=self.cert_filename)
        self.access_token = json.loads(response.text)["access_token"]
        logger.info("Клиент получил токен доступа")


    def log_models_names(self) -> None:
        """
        Получить список моделей
        """
        payload={}
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        response = requests.get(self.url_models, headers=headers, data=payload, timeout=30, verify=self.cert_filename)
        logger.info(f"models names: {[model['id'] for model in json.loads(response.text)["data"]]}")


    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict:
        """
        Генерация ответа модели.
        Args:
        prompt: Текстовый запрос к модели
        temperature: Параметр креативности (0.0-1.0)
        - 0.0-0.3: точные, детерминированные ответы
        - 0.5-0.7: сбалансированные ответы
        - 0.8-1.0: креативные ответы
        max_tokens: Максимальное количество токенов в ответе
        Returns:
        dict: Ответ API со структурой:
        {
        "text": str,
        # Сгенерированный текст
        "tokens_input": int,
        # Количество входных токенов
        "tokens_output": int, # Количество выходных токенов
        "raw_response": dict
        # Полный ответ API
        }
        Raises:
        requests.exceptions.RequestException: При ошибке сети
        ValueError: При неверном ответе API
        """

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "Вы — полезный ассистент. Отвечайте точно и по делу. Используйте русский язык."},
                {"role": "user", "content": prompt}
            ],
            # "function_call": "auto"
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }

        logger.info(f"Отправка запроса к API. Длина промпта: {len(prompt)} символов")
        try:
            response = requests.post(self.url_api, json=payload, headers=headers, timeout=30, verify=self.cert_filename)
            response.raise_for_status()
            result = response.json()

            # Проверка структуры ответа
            if "choices" not in result:
                raise ValueError("Некорректный формат ответа API: отсутствует 'choices'")

            if len(result["choices"]) == 0:
                raise ValueError("Пустой ответ от модели")
            generated_text = "".join(choice.get("message", {}).get("content", "") for choice in result["choices"])
            tokens_info = result.get("usage", {})
            response_data = {
                "text": generated_text,
                "tokens_input": tokens_info.get("prompt_tokens", 0),
                "tokens_output": tokens_info.get("completion_tokens", 0),
                "raw_response": result
            }
            logger.info(f"Запрос выполнен. Выходных токенов: {response_data['tokens_output']}")
            return response_data
        except requests.exceptions.Timeout:
            logger.error("Превышено время ожидания ответа от API")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса: {e}")
            raise
        except ValueError as e:
            logger.error(f"Ошибка парсинга ответа: {e}")
            raise


    def test_connection(self) -> bool:
        """
        Проверка подключения к API.
        Returns:
        bool: True если подключение успешно
        """
        try:
            # test_prompt = "Ответь одним словом: работает"
            test_prompt = 'В ответе требуется фраза из 1 слова в нижнем регистре без дополнений, без исправлений, без использования синонимов: "работает"'
            response = self.generate(test_prompt, temperature=0.1)
            return "работает" in response["text"].lower()
        except Exception as e:
            logger.error(f"Тест подключения не пройден: {e}")
            return False



def main():
    """
    Точка входа для тестирования клиента.
    """
    print("=" * 80)
    print("ЛАБОРАТОРНАЯ РАБОТА No1")
    print("Тестирование GigaChat API")
    print("=" * 80)

    # Загрузка переменных окружения
    load_dotenv()
    GIGACHAT_AUTHORIZATION_KEY = os.getenv("GIGACHAT_AUTHORIZATION_KEY")

    # Проверка наличия ключей
    if not GIGACHAT_AUTHORIZATION_KEY:
        print("\n❌ ОШИБКА: Не найден GIGACHAT_AUTHORIZATION_KEY")
        print("Создайте файл .env и добавьте переменную GIGACHAT_AUTHORIZATION_KEY")
        sys.exit(1)
    print("\n✅ Переменные окружения загружены")

    # Инициализация клиента
    try:
        client = GigaChatClient(GIGACHAT_AUTHORIZATION_KEY)
        print("✅ Клиент инициализирован")
    except Exception as e:
        print(f"\n❌ ОШИБКА инициализации: {e}")
        sys.exit(1)

    # Получение токена доступа
    # TODO: отслеживать 30 минутные сессии или выполнять обновление токена при каждом запросе
    print("\nНачало сессии: получение доступа")
    client.auth()

    # print("Получение списка моделей")
    # client.log_models_names()

    # Тест подключения
    print("🔄 Проверка подключения...")
    if client.test_connection():
        print("✅ Подключение успешно")
    else:
        print("❌ Подключение не удалось")
        sys.exit(1)

    # Базовый тестовый запрос
    print("\n" + "=" * 80)
    print("ТЕСТОВЫЙ ЗАПРОС")
    print("=" * 80)
    test_prompt = "Объясни кратко, что такое искусственный интеллект (не более 100 слов)"
    print(f"\nЗапрос: {test_prompt}\n")
    try:
        response = client.generate(test_prompt, temperature=0.5)
        print("ОТВЕТ МОДЕЛИ:")
        print("-" * 80)
        print(response["text"])
        print("-" * 80)
        print(f"\nСтатистика:")
        print(f" • Входные токены: {response['tokens_input']}")
        print(f" • Выходные токены: {response['tokens_output']}")
        print(f" • Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"\n❌ ОШИБКА выполнения запроса: {e}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("ЛАБОРАТОРНАЯ РАБОТА No1 ВЫПОЛНЕНА УСПЕШНО")
    print("=" * 80)


if __name__ == "__main__":
    main()
