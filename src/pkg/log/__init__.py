
LOG_FILE = 'log.txt'

f = open(LOG_FILE, 'a+')


def log(lvl, msg, *args, **kwargs):
    record_text = f'[{lvl}]: {msg} {args} {kwargs}'
    print(record_text)
    f.write(record_text + '\n')


def info(msg, *args, **kwargs):
    log('Info', msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    log('Warning', msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    log('Error', msg, *args, **kwargs)
