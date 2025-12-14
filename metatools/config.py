import configparser
import logging
import pkg_resources
import os

configfile = pkg_resources.resource_filename(__name__, "config.ini")
override_file = os.getenv("TMI_CONFIG")
override_logging = os.getenv("TMI_LOGGING")

config = configparser.ConfigParser()
config.read(configfile)
if override_file:
    config.read(override_file)

if not config.has_option("database", "connection"):
    print("ERROR: No database connection found in {0}".format(configfile))

def defaultEnd():
    if config.has_option("defaults", "end-date"):
        end_date = config["defaults"]["end-date"]
        if end_date != 'None' and end_date != '':
            return end_date
    return None

def defaultBegin():
    return config['defaults']['begin-date']

def getLogger(name):
    logging.basicConfig()
    logger = logging.getLogger(name)
    if config.has_option("defaults", "logging"):
        logger.setLevel(config["defaults"]["logging"])
    if override_logging:
        logger.setLevel(override_logging)
    return logger
