from pywikibot import family

class Family(family.Family):
    name = "localhost"
    langs = {"en": "localhost:4000"}

    def scriptpath(self, code):
        return ""

    def protocol(self, code):
        return "http"