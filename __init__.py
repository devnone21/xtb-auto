import logging.config
import os.path


logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'rotating': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'default',
            'filename': 'logs/xtb.log',
            'when': 'midnight',
            'backupCount': 3
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'CRITICAL',
            'propagate': True
        },
        'xtb': {
            'handlers': ['rotating'],
            'level': 'DEBUG'
        }
    }
})
