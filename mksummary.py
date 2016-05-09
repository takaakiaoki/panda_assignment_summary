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

    Args:
        d (pathlib.Path): folder name to parse

    Returns:
        dictionary of folder contents,
        {'dirname': str()   # name of folder
         'timestamp': None, # content of timestamp.txt
         'submissionText': None,      # content of (dirname)_submissionText.html
         'attachments': []  # attached files; list of pathlib.Path()
         }
    """

    obj = {'dirname': str(d),
           'timestamp': None,
           'submissionText': None,
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

        # html テキスト d.name + '_submissionText.html'
        spath = d / (d.name + '_submissionText.html')
        if spath.exists():
            # BOM付きutf8
            obj['submissionText'] = spath.open('r', encoding='utf-8-sig').read()


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

    # フォルダを巡回し, コンテンツのリストを作る.
    personal_dirs = list(walk_personal_dirs(root))
    
    print('<!DOCTYPE html>\n', file=writer)
    print('<html>\n', file=writer)
    print('  <meta charset="{0:s}">'.format(html_output_encoding), file=writer)
    print('  <style type="text/css">', file=writer)
    print('''
div.submissionText {
	background: #f0f0f0;
	border: medium solid #0f0f0f;
	font-size: medium;
        margin: 0 auto;
        width: 90%;
}''', file=writer)
    print('  </style>', file=writer)
# 一覧表表示の JavaScript 
    print('''
<script language="JavaScript">
function makeScoreWindow() {
var page= window.open();
page.document.open();
page.document.write("<html><body><table border>");
page.document.write("<tr><th>ID</th><th>氏名</th><th>得点</th></tr>");
''', file=writer)
#
# 履修者の個々の表，form の値を参照してつくる
#
    for p in personal_dirs:
        # フォルダ名を表示
        stu, stid = (p['dirname'].split(','))
        stid = stid.replace('(','').replace(')','')
        print('page.document.write("<tr><td>{0:s}</td>")'.format(stid), file=writer)
        print('page.document.write("<td>{0:s}</td>")'.format(stu), file=writer)
        print('page.document.write("<td>",document.form2.s{0:s}.value,"</td>")'.format(stid),file=writer)
        print('page.document.write("</tr>")',file=writer)

    print('''
page.document.write("<\/body><\/html>");
page.document.close();
}

</script>
<form>
記入した点数で別 window に一覧表を作る
<input type="button" value="採点表" onClick="makeScoreWindow()">
</form>
''', file=writer)


    print('<body><form name="form2">', file=writer)

    for p in personal_dirs:
        # フォルダ名を表示
        print('<hr><h3>{0:s}</h3>'.format(p['dirname']), file=writer)
        
        # 採点用フォームを表示
        stu, stid = (p['dirname'].split(','))
        stid = stid.replace('(','').replace(')','')
        print(' 点数: <input type="text" value="100" name="s{0:s}"><br/>'.format(str(stid)), file=writer)

        # タイムスタンプでコンテンツを確認
        if p['timestamp'] is None:
            print('提出未確認<br>', file=writer)
        else:
            # タイムスタンプ
            print('timestamp: {0:s}<br>'.format(str(p['timestamp'])), file=writer)
            # HTML
            if p['submissionText']:
                print('submissionText:<br/>', file=writer)
                print('<div class="submissionText">', file=writer)
                print(p['submissionText'], file=writer)
                print('</div>', file=writer)
            # 添付ファイル
            if p['attachments']:
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
                        print('<img src="{0:s}" width=40%>'.format(linkurl),
                              end='', file=writer)
                    else:
                        print(relurl, end='', file=writer)
                    print('</a><br/>', file=writer)

    print('</from></body></html>', file=writer)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('output', nargs='?', type=str, default='summary.html',
            help='default output filename (default: %(default))')
    parser.add_argument('--root', type=str, default='.',
            help='root directory (default: %(default))')

    args = parser.parse_args()

    with open(args.output, 'wb') as output_buffer:
        main(output_buffer, root=pathlib.Path(args.root))
