import pathlib
import pytz
import datetime
import urllib
import re
import io
import sys
import argparse


def foreachpersonaldir(d):
    """個人フォルダの中をパースし, 必要な情報を取り出す
    """

    obj = {'dirname': str(d),
           'timestamp': None,
           'attachments': []}

    tpath = d / 'timestamp.txt'
    if tpath.exists():
        tstext = tpath.open('r').read()  # for > py3.5 tpath.read_text() is smart
        tstamp = datetime.datetime.strptime(tstext[:14], '%Y%m%d%H%M%S')
        # loaded timestamp is in utc, translate to jst
        # see http://nekoya.github.io/blog/2013/06/21/python-datetime/
        tstamp = pytz.utc.localize(tstamp)  # attatch tzinfo as utc
        tstamp = tstamp.astimezone(pytz.timezone('Asia/Tokyo')) # apply JST
        obj['timestamp'] = tstamp

        # show submitted files
        attachment_dir = d / '提出物の添付'
        for f in attachment_dir.glob('*'):
            obj['attachments'].append(f)

    return obj


def walk_personal_dirs(root=pathlib.Path('.')):
    """パス上のフォルダを検索し, foreachpersondir のコンテンツをiterativeに取得する.

    Args:
        root (pathlib.Path) 検索開始パス
    """

    dirs = root.glob('*,(*)')
    for d in dirs:
        # () 内のIDを取り出す.
        reobj = re.compile(u'.+,\((?P<id>[0-9x]+)\)')
        mobj = reobj.match(d.name)
        if mobj:
            # フォルダの中をパースする.
            yield foreachpersonaldir(d)

def main(output_buffer, root=pathlib.Path('.'), html_output_encoding='utf-8'):
    """
    Args:
        output_buffer (File): binary IO to output
        root: root path to walk
        html_output_encoding: encoding for output html
    """

    writer = io.TextIOWrapper(output_buffer, encoding=html_output_encoding, newline='\n')
    
    print('<!DOCTYPE html>\n', file=writer)
    print('<html>\n', file=writer)
    print('  <meta charset="{0:s}">'.format(html_output_encoding), file=writer)
    print('<body>', file=writer)

    for p in walk_personal_dirs(root):
        # フォルダ名を表示
        print('<hr><h3>{0:s}</h3>'.format(p['dirname']), file=writer)
        
        # タイムスタンプでコンテンツを確認
        if p['timestamp'] is None:
            print('提出未確認<br/>', file=writer)
        else:
            # タイムスタンプ
            print('timestamp: {0:s}<br/>'.format(str(p['timestamp'])), file=writer)
            # 添付ファイル
            print('attachments:<br/>', file=writer)
            for a in p['attachments']:
                # リンクパスをurl形式に変換
                relurl = urllib.parse.urlunsplit(('', '', str(a.as_posix()), '', ''))
                # in sake for working on IE11 and Edge (and other browsers)
                # do not escape multibyte URL
                # linkurl = urllib.parse.quote(relurl)
                linkurl = relurl
                print('<a href="{0:s}">'.format(linkurl), end='', file=writer)
                if a.suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp'):
                    print(relurl, '<br/>', sep='', end='', file=writer)
                    # ビットマップならば埋め込み
                    print('<img src="{0:s}" width=40%>'.format(linkurl), end='', file=writer)
                else:
                    print(relurl, end='', file=writer)
                print('</a><br/>', file=writer)

    print('</body></html>', file=writer)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('output', nargs='?', type=str, default='summary.html',
            help='default output filename (default: %(default))')
    parser.add_argument('--root', type=str, default='.',
            help='root directory (default: %(default))')

    args = parser.parse_args()

    with open(args.output, 'wb') as output_buffer:
        main(output_buffer, root=pathlib.Path(args.root))
