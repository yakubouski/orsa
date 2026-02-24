import logging
import sys

RESET = "\x1b[0m"
COLORS = {
    "DEBUG":    "\x1b[90m",  # cyan
    "INFO":     "\x1b[32m",  # green
    "WARNING":  "\x1b[33m",  # yellow
    "ERROR":    "\x1b[31m",  # red
    "CRITICAL": "\x1b[41m",  # red background
}

class __log_formater(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not getattr(record,'saga',None):
            record.saga = ""
        
        if getattr(record,'kind',None):
            record.name = f"{record.name}:{record.kind}"

        levelname = record.levelname
        try:
            if levelname != "DEBUG":
                record.levelname = f"{COLORS[levelname]}{levelname}{RESET}"
                return super().format(record)
            else:
                return COLORS[levelname]+super().format(record)+RESET
        finally:
            record.levelname = levelname

def getLogger(name, colored = True) -> logging.Logger:
    _logger = logging.getLogger(name)
    if not _logger.handlers:
        _logHandler = logging.StreamHandler()
        if colored and (1 or sys.stdout.isatty()):
            _logHandler.setFormatter(__log_formater('%(levelname)s:%(name)s%(saga)s: %(message)s'))
        else:
            _logHandler.setFormatter(logging.Formatter('%(levelname)s:%(name)s%(saga)s: %(message)s'))
        _logger.addHandler(_logHandler)
        _logger.propagate = False
    return _logger