import datetime
import ntpath
import os
import os.path
import re
from datetime import timedelta
from pathlib import Path
from threading import Timer

import dateutil
import requests

FLOCKLAB_ADDRESS = 'https://www.flocklab.ethz.ch/user'
FLOCKLAB_SERIAL_ADDRESS = "whymper.ee.ethz.ch"
FLOCKLAB_SERIAL_BASE_PORT = 50100

START_TIME_OFFSET = 120


class WindowsInhibitor:
    '''Prevent OS sleep/hibernate in windows; code from:
    https://github.com/h3llrais3r/Deluge-PreventSuspendPlus/blob/master/preventsuspendplus/core.py
    API documentation:
    https://msdn.microsoft.com/en-us/library/windows/desktop/aa373208(v=vs.85).aspx'''
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001

    def __init__(self):
        pass

    def inhibit(self):
        import ctypes
        print("Preventing Windows from going to sleep")
        ctypes.windll.kernel32.SetThreadExecutionState(
            WindowsInhibitor.ES_CONTINUOUS | \
            WindowsInhibitor.ES_SYSTEM_REQUIRED)

    def uninhibit(self):
        import ctypes
        print("Allowing Windows to go to sleep")
        ctypes.windll.kernel32.SetThreadExecutionState(
            WindowsInhibitor.ES_CONTINUOUS)


class FlockLab:
    def __init__(self):
        self.callback = None
        self.osSleep = None

        self.auth = {}
        home_auth = os.path.join(str(Path.home()), '.flocklabauth')

        if os.path.isfile('.flocklabauth'):
            self.auth = self.parse_auth('.flocklabauth')
        elif os.path.isfile(home_auth):
            self.auth = self.parse_auth(home_auth)
        else:
            raise Exception("Error. No auth information given!")

        if not 'USER' in self.auth or not 'PASSWORD' in self.auth:
            raise Exception("Error. Auth information not in correct format! "
                            "You have to place the file '.flocklabauth' under your home or working directory."
                            "See https://gitlab.ethz.ch/tec/public/flocklab/wikis/Man/Tutorials/Tutorial7")

    def parse_auth(self, authfile):
        envre = re.compile(r'''^([^\s=]+)=(?:[\s"']*)(.+?)(?:[\s"']*)$''')
        result = {}
        with open(authfile) as ins:
            for line in ins:
                match = envre.match(line)
                if match is not None:
                    result[match.group(1)] = match.group(2)
        return result

    def schedule_test(self, xmlfile, callback=None):
        self.callback = callback

        url = "{}/{}".format(FLOCKLAB_ADDRESS, '/newtest.php')

        files = {'xmlfile': (ntpath.basename(xmlfile), open(xmlfile, 'rb'), 'application/xml')}

        r = requests.post(url,
                          data={'username': self.auth['USER'],
                                'password': self.auth['PASSWORD'],
                                'first': 'no',
                                },
                          files=files)

        success_regex = '<!-- cmd --><p>Test \(Id [0-9]*\) successfully added\.</p><!-- cmd -->'

        if re.search(success_regex, r.text):
            regex = '.*<!-- flocklabscript,([0-9]*),([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+[0-9]{4}),([0-9]*)-->.*'

            m = re.search(regex, r.text)

            test = {
                'id': m.group(1),
                'start_time': dateutil.parser.parse(m.group(2))
            }

            print("Test successfully added to FlockLab. Test (ID {}) starts on {}".format(test['id'], test['start_time']))

            if self.callback is not None:
                delta = test['start_time'] - datetime.datetime.now(datetime.timezone.utc) + timedelta(seconds=START_TIME_OFFSET)
                print("Experiment callback will start in {}.".format(delta))

                self.osSleep = None
                # in Windows, prevent the OS from sleeping while we run
                if os.name == 'nt':
                    self.osSleep = WindowsInhibitor()
                    self.osSleep.inhibit()

                t = Timer(delta.seconds, self.handle_callback)
                t.start()  # Start after delta time
        else:
            print(r.text)
            raise Exception("Error. Auth information wrong, file not validated or connected via IPv6!")

    def handle_callback(self):
        if self.osSleep:
            self.osSleep.uninhibit()
