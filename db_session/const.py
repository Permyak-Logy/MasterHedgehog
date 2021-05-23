import datetime

# Минимальное время в DateTime
MIN_DATETIME = datetime.datetime.fromtimestamp(0).date()

# Права для команд по умолчанию
DEFAULT_ACCESS = {
    "command": None,
    "admin": True,
    "everyone": False,
    "min_client_time": 0,
    "min_member_time": 0,
    "min_role": None,
    "roles": [],
    "users": [],
    "channels": [],
    "exc_roles": [],
    "exc_users": [],
    "exc_channels": [],
    "active": True
}

MAX_BIGINT = 9223372036854775807
MIN_BIGINT = -9223372036854775808
