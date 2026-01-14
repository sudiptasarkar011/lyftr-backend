import logging
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger
from app.config import settings

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('ts'):
            log_record['ts'] = datetime.utcnow().isoformat()
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

logger = logging.getLogger("lyftr_logger")
logHandler = logging.StreamHandler()
formatter = CustomJsonFormatter('%(ts)s %(level)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(settings.log_level)