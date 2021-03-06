import configparser
import pkg_resources

configfile = pkg_resources.resource_filename(__name__, "config.ini")
config = configparser.ConfigParser()
config.read(configfile)
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
