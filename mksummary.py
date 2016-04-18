import pathlib
import pytz
import datetime
import urllib

srcpath = pathlib.Path('.')

class Writer(object):
    def root_in(self):
        pass

    def root_out(self):
        pass


class HTMLWriter(Writer):
    def root_in(self):
        print('<html><body><br/>')

    def root_out(self):
        print('</body></html>')

    def dirname(self, path):
        print('<hr/><h2>', str(path), '</h2>', sep='')

    def timestamp(self, dt):
        print('timestamp: ', str(dt), '<br/>', sep='')

    def attachment_in(self):
        print('attachments:<br/>')

    def attachment_elem(self, path):
        # if png
        relurl = urllib.parse.urlunsplit(('', '', str(path.as_posix()), '', ''))
        print(relurl, '<br/>', sep='')
        if path.suffix.lower() in ('.png', '.jpg', '.jpeg'):
            print('<img src="', relurl, '" width=640px><br/>', sep='')
        

class TextWriter(Writer):
    def dirname(self, path):
        print('dirname:', str(path))

    def timestamp(self, dt):
        print('  timestamp:', str(dt))

    def attachment_in(self):
        print('  attachments:')

    def attachment_elem(self, path):
        print('    -', str(path))


def foreachpersonaldir(d, writer):
    # print dirname
    writer.dirname(d)
    # show timestamp if exists
    tpath = d / 'timestamp.txt'
    if tpath.exists():
        tstext = tpath.read_text()
        tstamp = datetime.datetime.strptime(tstext[:14], '%Y%m%d%H%M%S')
        # loaded timestamp is in utc, translate to jst
        # see http://nekoya.github.io/blog/2013/06/21/python-datetime/
        tstamp = pytz.utc.localize(tstamp)  # attatch tzinfo as utc
        tstamp = tstamp.astimezone(pytz.timezone('Asia/Tokyo')) # apply JST
        writer.timestamp(tstamp)

        # show submitted files
        attachment_dir = d / '提出物の添付'
        writer.attachment_in()
        for f in attachment_dir.glob('*'):
            writer.attachment_elem(f)

def main():

    # writer = TextWriter()
    writer = HTMLWriter()
    writer.root_in()

    dirs = srcpath.glob('*,(*)')
    for d in dirs:
        foreachpersonaldir(d, writer)

    writer.root_out()

if __name__ == '__main__':
    main()
