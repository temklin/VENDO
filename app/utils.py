from passlib.context import CryptContext

from datetime import datetime, timedelta


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password : str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)



MONTHS = {1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
          5: 'мая', 6: 'июня', 7: "июля", 8: 'августа',
          9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'}

def format_date(dt, with_time=True):
    if not dt:
        return ''
    now = datetime.now()
    today = now.date()
    if dt.date() == today:
        day_str = "Сегодня"
    elif dt.date() == today - timedelta(days=1):
        day_str = "Вчера"
    elif dt.date() == today - timedelta(days=2):
        day_str = "Позавчера"
    else:
        day_str = f"{dt.day} {MONTHS[dt.month]}"
    if with_time:
        return f"{day_str} в {dt.strftime('%H:%M')}"
    return day_str


def format_price(value):
    if value is None:
        return ''
    try:
        return f"{int(value):,}".replace(',', ' ')
    except (ValueError, TypeError):
        return str(value)