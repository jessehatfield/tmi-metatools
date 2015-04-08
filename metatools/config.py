import configparser
import pkg_resources

configfile = pkg_resources.resource_filename(__name__, "config.ini")
config = configparser.ConfigParser()
config.read(configfile)
if not config.has_option("database", "connection"):
    print("ERROR: No database connection found in {0}".format(configfile))

def defaultEnd():
    if config.has_option("defaults", "end-date"):
        return config["defaults"]["end-date"]
    else:
        return None
