from functools import wraps
import json
import os
import time

PERFORMANS_LOG_DOSYASI = "asevi_performans_loglari.json"


def bellek_kullanimi_al(process_factory=None, pid_fn=None):
  """Return current process RSS in MB; degrade gracefully if unavailable."""
  try:
    if process_factory is None:
      import psutil
      process_factory = psutil.Process
    if pid_fn is None:
      pid_fn = os.getpid
    process = process_factory(pid_fn())
    return round(process.memory_info().rss / (1024 * 1024), 1)
  except Exception:
    return 0.0


def performans_logu_kaydet(islem_adi, gecen_sure):
  loglar = []
  if os.path.exists(PERFORMANS_LOG_DOSYASI):
    try:
      with open(PERFORMANS_LOG_DOSYASI, "r", encoding="utf-8") as f:
        loglar = json.load(f)
    except Exception:
      loglar = []

  loglar.append({
      "tarih": time.strftime("%Y-%m-%d %H:%M:%S"),
      "islem": islem_adi,
      "sure_saniye": round(gecen_sure, 4),
  })

  # Son 500 logu tutarak dosyanın şişmesini önleyelim
  if len(loglar) > 500:
    loglar = loglar[-500:]

  with open(PERFORMANS_LOG_DOSYASI, "w", encoding="utf-8") as f:
    json.dump(loglar, f, ensure_ascii=False, indent=4)


# Fonksiyonların çalışma süresini ölçmek için Decorator
def sureyi_olc(islem_adi):
  def decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
      baslangic = time.time()
      sonuc = func(*args, **kwargs)
      bitis = time.time()
      gecen = bitis - baslangic
      performans_logu_kaydet(islem_adi, gecen)
      return sonuc

    return wrapper

  return decorator
