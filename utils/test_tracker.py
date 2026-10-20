import os
import json
import threading

class TestTracker:
    """
    Rastreador de entidades creadas durante la sesión de pruebas.
    Permite que la suite sepa exactamente qué usuarios y negocios creó dinámicamente,
    eliminando la necesidad de listas 'quemadas' y garantizando que el teardown
    solo limpie lo que los tests crearon.
    """
    _lock = threading.Lock()
    _file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.tracked_test_entities.json"))

    @classmethod
    def _read_data(cls) -> dict:
        if os.path.exists(cls._file_path):
            try:
                with open(cls._file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"business_ids": [], "user_ids": []}

    @classmethod
    def _write_data(cls, data: dict):
        try:
            with open(cls._file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    @classmethod
    def track_business(cls, business_id: str):
        if not business_id:
            return
        with cls._lock:
            data = cls._read_data()
            if business_id not in data["business_ids"]:
                data["business_ids"].append(str(business_id))
                cls._write_data(data)

    @classmethod
    def track_user(cls, user_id: str):
        if not user_id:
            return
        with cls._lock:
            data = cls._read_data()
            if user_id not in data["user_ids"]:
                data["user_ids"].append(str(user_id))
                cls._write_data(data)

    @classmethod
    def get_tracked_entities(cls) -> dict:
        with cls._lock:
            return cls._read_data()

    @classmethod
    def clear(cls):
        with cls._lock:
            if os.path.exists(cls._file_path):
                try:
                    os.remove(cls._file_path)
                except Exception:
                    pass
