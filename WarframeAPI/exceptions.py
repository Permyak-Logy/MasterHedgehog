# WarframeAPI/exceptions.py

class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class DictTypeError(Error):
    """Error class to be raised when an incorrect object is passed to a class constructor."""

    def __init__(self, goal_class, dict_obj):
        self.goal_class = goal_class
        self.dict_obj = dict_obj
        self.message = 'Was expecting an object of type dict that matches the '
        self.message += self.goal_class + ' class, got an object of type '
        self.message += str(type(self.dict_obj)) + ' instead.'


class NonPlatformError(Error):
    """Error class to be raised when an invalid platform is called in the constructor of a wf_api"""

    def __init__(self, fake_platform):
        self.fake_platform = fake_platform
        self.message = str(fake_platform) + ' is not a valid platform. '
        self.message += 'Pass \'pc\', \'ps4\', \'xb1\', or \'swi\'.'


class NonLanguageError(Error):
    def __init__(self, fake_language):
        self.fake_language = fake_language
        self.message = str(fake_language) + ' is not a valid language'
        self.message += 'Pass "de", "es", "fr", "it", "ko", "pl", "pt", "ru", "zh" or "en"'


class StatusCodeError(Error):
    """Error class to be raised when a response object does not have a 200 status code."""

    def __init__(self, actual_code, call_name):
        self.actual_code = actual_code
        self.call_name = call_name
        self.message = 'Warning: response object from API call ' + self.call_name
        self.message += ' returned with a status code of ' + str(self.actual_code)
        self.message += ', not 200. Forwarding response object anyway.'
