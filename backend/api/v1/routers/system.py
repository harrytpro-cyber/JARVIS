"""Stats système temps réel via psutil. Pas d'auth requise (données locales)."""
from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/stats")
async def system_stats():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        cpu_temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        cpu_temp = round(entries[0].current, 1)
                        break
        except (AttributeError, NotImplementedError):
            pass

        return {
            "cpu_percent": round(cpu, 1),
            "ram_percent": round(ram.percent, 1),
            "ram_used_gb": round(ram.used / 1e9, 2),
            "ram_total_gb": round(ram.total / 1e9, 2),
            "disk_percent": round(disk.percent, 1),
            "cpu_temp": cpu_temp,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except ImportError:
        return {
            "cpu_percent": 0, "ram_percent": 0,
            "ram_used_gb": 0, "ram_total_gb": 0,
            "disk_percent": 0, "cpu_temp": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": "psutil non disponible",
        }
