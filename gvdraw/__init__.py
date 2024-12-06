import logging
FMT="%(asctime)s.%(msecs)01d %(name)s@%(lineno)d [%(levelname)s]: %(message)s"
DATEFMT = "%m-%d %H:%M:%S"
logging.basicConfig(level=logging.INFO, format=FMT, datefmt=DATEFMT)
