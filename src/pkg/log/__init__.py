

def log(lvl, msg, *args, **kwargs):
    print(f'[{lvl}]: {msg} {args} {kwargs}')

def info(msg, *args, **kwargs):
    log('Info', msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    log('Warning', msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    log('Error', msg, *args, **kwargs)