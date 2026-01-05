from loguru import logger

VALID_TYPES = {"appearance": "внешность", "character": "характер", "achievements": "достижения"}

def normalize_type(t: str) -> str:
    t = (t or "").strip().lower()
    # поддержать русские слова
    if t in ["внешность", "внешний", "внешний вид"]:
        return "appearance"
    if t in ["характер", "личность"]:
        return "character"
    if t in ["достижения", "успехи", "работа", "career", "учёба"]:
        return "achievements"
    if t in VALID_TYPES:
        return t
    return "character"  # default
