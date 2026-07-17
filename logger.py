"""
Registro de ejecución de Sophia (requisito del desafío: trazabilidad).

Guarda cada interacción en logs/sophia_log.jsonl con:
pregunta, contexto/fuentes usadas, respuesta, timestamp, tiempo de respuesta.
"""

import os
import json
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "logs", "sophia_log.jsonl")


def registrar_interaccion(pregunta, respuesta, fuentes, tiempo_respuesta_seg):
    """Agrega una línea al log en formato JSON Lines (una interacción por línea)"""
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    entrada = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pregunta": pregunta,
        "respuesta": respuesta,
        "fuentes": fuentes,
        "tiempo_respuesta_seg": round(tiempo_respuesta_seg, 2),
    }

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


class Cronometro:
    """Utilidad simple para medir cuánto tarda cada consulta"""

    def __enter__(self):
        self._inicio = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.duracion = time.perf_counter() - self._inicio
