#
# -*- coding: utf-8 -*-

import pathlib
import pytz
import datetime
import urllib
import re
import io
import sys
import argparse


def foreachpersonaldir(d, root=pathlib.Path('.')):
    """個人フォルダの中をパースし, 必要な情報を取り出す

    Args:
        d (pathlib.Path): folder name to parse
        root (pathlib.Path): root directory

    Returns:
        dictionary of folder contents,
        {'dirname': str()   # name of folder, relative to root
         'timestamp': None, # content of timestamp.txt
         'submissionText': None,      # content of (dirname)_submissionText.html
         'attachments': []  # attached files; list of pathlib.Path() relative to root
         }
    """

    obj = {'dirname': str(d.relative_to(root)),
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
            obj['attachments'].append(f.relative_to(root))

    return obj


def walk_personal_dirs(root=pathlib.Path('.')):
    """パス上のフォルダを検索し, foreachpersondir のコンテンツをiterativeに取得する.

    Args:
        root (pathlib.Path) 検索開始パス
    """

    dirs = root.glob('*,(*)')
    for d in dirs:
        # '氏名, (ID)' の形式に合致したフォルダだけを採用. 
        if d.is_dir():
            reobj = re.compile(u'.+,\((?P<id>[0-9x]+)\)')
            mobj = reobj.match(d.name)
            if mobj:
                # フォルダの中をパースする.
                yield foreachpersonaldir(d, root)

def main(output_buffer, root=pathlib.Path('.'), assignmentname='', html_output_encoding='utf-8'):
    """
    Args:
        output_buffer (File): binary IO to output
        root: root path to walk
        assignmentname: title of HTML page
        html_output_encoding: encoding for output html
    """

    writer = io.TextIOWrapper(output_buffer, encoding=html_output_encoding, newline='\n')

    # フォルダを巡回し, コンテンツのリストを作る.
    personal_dirs = list(walk_personal_dirs(root))
    
    # HTML の出力
    print('<!DOCTYPE html>\n', file=writer)
    print('<html>', file=writer)
    print('<head>', file=writer)
    print('  <meta charset="{0:s}">'.format(html_output_encoding), file=writer)
    print('  <title>{0:s}</title>'.format(assignmentname), file=writer)
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
<script type="text/javascript">
function makeScoreWindow() {
var page= window.open();
page.document.open();
page.document.write("<html>");''', file=writer)
    print('page.document.write("<head><title>点数表(score sheet): {0:s}</title></head>");'.format(assignmentname), file=writer)
    print('page.document.write("<body>");', file=writer)
    print('page.document.write("<H1>点数表(score sheet): {0:s}</H1>");'''.format(assignmentname), file=writer)
    print('''
page.document.write("表はコピー&amp;ペーストで表計算ソフトなどに貼り付けてご利用ください.<br>");
page.document.write("(Use this table on your spread sheet software with copy &amp; paste.)<hr>");
page.document.write("<table border>");
page.document.write("<tr><th>ID</th><th>氏名(Name)</th><th>点数(score)</th></tr>");
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
page.document.write("</body></html>");
page.document.close();
}

</script>''', file=writer)
    print('</head>', file=writer)
    print('<body>', file=writer)
    print('<H1>{0:s}</H1>'.format(assignmentname), file=writer)
    print('''
<form>
記入した点数で別 window に点数表を作る<br>
(Make a score sheet on another window)<br>
<input type="button" value="点数表表示(show score sheet)" onClick="makeScoreWindow()">
</form>
''', file=writer)

    print('<form name="form2">', file=writer)

    for p in personal_dirs:
        # フォルダ名を表示
        print('<hr><h3>{0:s}</h3>'.format(p['dirname']), file=writer)
        
        # 採点用フォームを表示
        stu, stid = (p['dirname'].split(','))
        stid = stid.replace('(','').replace(')','')

        # タイムスタンプでコンテンツを確認
        if p['timestamp'] is None:
            # デフォルトの成績を0
            print('点数(score): <input type="text" value="0" name="s{0:s}"> (0-100)<br>'.format(str(stid)), file=writer)
            print('提出未確認(materials not found)<br>', file=writer)
        else:
            # デフォルトの成績を100
            print('点数(score): <input type="text" value="100" name="s{0:s}"> (0-100)<br>'.format(str(stid)), file=writer)
            # タイムスタンプ
            print('timestamp: {0:s}<br>'.format(str(p['timestamp'])), file=writer)
            # HTML
            if p['submissionText']:
                print('submissionText:<br>', file=writer)
                print('<div class="submissionText">', file=writer)
                print(p['submissionText'], file=writer)
                print('</div>', file=writer)
            # 添付ファイル
            if p['attachments']:
                print('attachments:<br>', file=writer)
                for a in p['attachments']:
                    # リンクパスをurl形式に変換
                    relurl = urllib.parse.urlunsplit(('', '', str(a.as_posix()), '', ''))
                    # in sake for working on IE11 and Edge (and other browsers)
                    # do not escape multibyte URL
                    # linkurl = urllib.parse.quote(relurl)
                    linkurl = relurl
                    print('<a href="{0:s}">'.format(linkurl), end='', file=writer)
                    if a.suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp'):
                        print(relurl, '<br>', sep='', end='', file=writer)
                        # ビットマップならば埋め込み
                        print('<img src="{0:s}" width=40%>'.format(linkurl),
                              end='', file=writer)
                    else:
                        print(relurl, end='', file=writer)
                    print('</a><br>', file=writer)

    print('</from></body></html>', file=writer)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('root', nargs='?', type=str, default='.',
            help='root directory or file path under root (default: %(default)s). If file path is given, directory part is used as ROOT')
    parser.add_argument('--output', type=str, default='summary.html',
            help='default output filename (default: %(default)s). file is output as "ROOT/OUTPUT"')

    args = parser.parse_args()

    rootpath = pathlib.Path(args.root)
    if rootpath.is_file():
        rootpath = rootpath.parent

    outputpath = rootpath / args.output

    # rootpathの名前をタイトルにする
    assignmentname = rootpath.absolute().name

    with outputpath.open('wb') as output_buffer:
        main(output_buffer, root=rootpath, assignmentname=assignmentname)
