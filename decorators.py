"""Обработка ошибок, подтверждение действий и кэш выборок."""

import time


def handle_db_errors(function):
    """Показать ошибку команды и вернуть управление консоли."""

    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except KeyError as error:
            print(f"Ошибка: Таблица или столбец {error} не найден.")
        except ValueError as error:
            print(f"Ошибка валидации: {error}")
        except FileNotFoundError:
            print("Ошибка: Файл данных не найден.")
        except OSError:
            print("Ошибка: Не удалось прочитать или сохранить файл данных.")
        return None

    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    return wrapper


def confirm_action(action_name):
    """Запросить подтверждение перед удалением."""

    def decorate(function):
        def wrapper(*args, **kwargs):
            answer = input(f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: ')
            if answer.strip().lower() != "y":
                print("Операция отменена.")
                return None
            return function(*args, **kwargs)

        wrapper.__name__ = function.__name__
        wrapper.__doc__ = function.__doc__
        return wrapper

    return decorate


def log_time(function):
    """Замерить продолжительность операции."""

    def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            return function(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - start
            print(f"Функция {function.__name__} выполнилась за {elapsed:.3f} секунд")

    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    return wrapper


def create_cacher():
    """Вернуть функцию с собственным кэшем в замыкании."""
    cache = {}

    def cache_result(key, value_func):
        if key not in cache:
            cache[key] = value_func()
        return cache[key]

    cache_result.clear = cache.clear
    return cache_result
