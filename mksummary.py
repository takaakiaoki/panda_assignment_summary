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
        tstamp = tstamp.astimezone(pytz.timezone('Asia/Tokyo'))  # apply JST
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
        # for English mode
        attachment_dir = d / 'Submission attachment(s)'
        for f in attachment_dir.glob('*'):
            obj['attachments'].append(f.relative_to(root))

    return obj


def walk_personal_dirs(root=pathlib.Path('.')):
    """パス上のフォルダを検索し, foreachpersondir のコンテンツをiterativeに取得する.

    Args:
        root (pathlib.Path) 検索開始パス

    Yields:
        {
            id (str): 学生番号
            name (str): 氏名
            personaldir: None or (result from foreachpersonaldir)
        }
    """

    # 5/21 以降のフォーマット
    dirs = root.glob('* (*)')
    for d in dirs:
        # '氏名 (ID)' の形式に合致したフォルダだけを採用. 
        if d.is_dir():
            reobj = re.compile('(?P<name>.+) \((?P<id>[0-9x]+)\)')
            mobj = reobj.match(d.name)
            if mobj:
                # フォルダの中をパースする.
                yield {'id': mobj.group('id'),
                       'name': mobj.group('name'),
                       'personaldir': foreachpersonaldir(d, root)}

    # 5/21 以前のフォーマット
    dirs = root.glob('*,(*)')
    for d in dirs:
        # '氏名, (ID)' の形式に合致したフォルダだけを採用. 
        if d.is_dir():
            reobj = re.compile('(?P<name>[^,]+),\((?P<id>[0-9x]+)\)')
            mobj = reobj.match(d.name)
            if mobj:
                # フォルダの中をパースする.
                yield {'id': mobj.group('id'),
                       'name': mobj.group('name'),
                       'personaldir': foreachpersonaldir(d, root)}


def render_personalfolder(p,
                          writer,
                          enable_viewerjs=False,
                          scorefield=None):
    """ foreachpersonaldir の内容を html で出力する.
    Args:
        p (dict): foreachpersonaldir の結果. None の場合, 'フォルダが確認できません' を出力
        writer (File): htmlの出力対象
        enable_viwerjs (optional[bool]): ViewerJS でのプレビューに対応する.
        scorefield (optional[dict]): 得点フォームの情報, Noneの場合不要
            score (int): 現在の点数, None だとデフォルト値を採用
            fullscore (int): 満点
            formname (str): このフォームの name 属性
    """
    def formatscoreform(s, defaulscore):
        '''点数フォームをフォーマットする

        Args:
            s (dict): 得点フォームの情報
                score (int): 現在の点数, None だとデフォルト値を採用
                fullscore (int): 満点
                formname (str): このフォームの name 属性
            defaultscore (int): s['score'] == None の場合に設定する値
        '''

        f = '点数(score): <input type="text" value="{0:d}" name="{2:s}"> (0-{1:d})<br>'
        return f.format(s['score'] if s['score'] is not None else 0,
                        s['fullscore'],
                        s['formname'])

    if p is None:
        if scorefield:
            print(formatscoreform(scorefield, 0), file=writer)
        print('フォルダがありません(personal folder is not found)<br>', file=writer)
        return

    # タイムスタンプでコンテンツを確認
    if p['timestamp'] is None:
        # デフォルトの成績を0
        if scorefield:
            print(formatscoreform(scorefield, 0), file=writer)
        print('提出未確認(materials not found)<br>', file=writer)
        return

    # 有効なコンテンツ
    # デフォルトの成績を100
    if scorefield:
        print(formatscoreform(scorefield, 100), file=writer)
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
        print('<div class="attachment">', file=writer)
        for a in p['attachments']:
            # リンクパスをurl形式に変換
            relurl = urllib.parse.urlunsplit(('', '', str(a.as_posix()), '', ''))
            # in sake for working on IE11 and Edge (and other browsers)
            # do not escape multibyte URL
            # linkurl = urllib.parse.quote(relurl)
            linkurl = relurl
            print('<a href="{0:s}">'.format(linkurl), end='', file=writer)
            suffix = a.suffix.lower()
            if suffix in ('.png', '.jpg', '.jpeg', '.bmp'):
                print(relurl, '<br/>', sep='', end='', file=writer)
                # ビットマップならば埋め込み
                print('<img class="attachedimg" src="{0:s}">'.format(linkurl),
                      end='', file=writer)
                print('</a><br/>', file=writer)
            elif enable_viewerjs and (suffix in ('.pdf', '.odf')):
                #  ViewerJS によるプレビュー画面埋め込み
                print(relurl, '</a><br/>', file=writer)
                print('<iframe class="attacheddoc" src="_summary/ViewerJS/#../../{0:s}"'
                      'allowfullscreen webkitallowfullscreen></iframe>'.format(linkurl),
                      end='', file=writer)
            else:
                print('{0:s}</a><br/>'.format(linkurl), file=writer)
        print('</div>', file=writer)


def scoresheetscript(personal_dirs, writer):
    """得点表を生成するjavascriptを作成する

    Args:
        personal_dirs (list): walk_personal_dirs_idlist が返すオブジェクトのリスト
        writer (stream): 出力するファイル
    """

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
        print('page.document.write("<tr><td>{0:s}</td>")'.format(p['id']), file=writer)
        print('page.document.write("<td>{0:s}</td>")'.format(p['name']), file=writer)
        print('page.document.write("<td>",document.form2.{0:s}.value,"</td></tr>")'.format('s'+p['id']),file=writer)

    print('''
page.document.write("</body></html>");
page.document.close();
}
</script>''', file=writer)


def main(output_buffer,
         root=pathlib.Path('.'),
         assignmentname='',
         html_output_encoding='utf-8',
         enable_viewerjs='False'):
    """
    root フォルダを巡回し, summary.html 等を出力する.

    Args:
        output_buffer (File): binary IO to output
        root (pathlib.Path): root path to walk
        assignmentname (str): title of HTML page
        html_output_encoding (str): encoding for output html
        enable_viwerjs (bool): ViewerJS でのプレビューに対応する.
    """

    writer = io.TextIOWrapper(output_buffer, encoding=html_output_encoding, newline='\n')

    # フォルダを巡回し, コンテンツのリストを作る.
    personal_dirs = list(walk_personal_dirs(root))

    # HTML の出力
    print('<!DOCTYPE html>', file=writer)
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
  margin: 0 0 0 10px;
  padding: 5px 10px 5px 10px;
}''', file=writer)
    print('''
img.attachedimg {
  width: 510px;
}
iframe.attacheddoc {
  width: 510px;
  height: 720px;
}
div.attachment {
  margin: 0 0 0 10px;
}''', file=writer)
    print('  </style>', file=writer)
    # 得点表生成
    scoresheetscript(personal_dirs, writer)
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
        print('<hr><h3>{0:s}</h3>'.format(p['personaldir']['dirname']), file=writer)
        
        # 採点用フォームデータ
        scorefield = {
            'formname': 's' + p['id'],
            'score': None,
            'fullscore': 100}
        render_personalfolder(p['personaldir'], writer,
                              enable_viewerjs=enable_viewerjs,
                              scorefield=scorefield)

    print('</form></body></html>', file=writer)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('root', nargs='?', type=str, default='.',
                        help='root directory or file path under root (default: %(default)s).'
                             'If file path is given, directory part is used as ROOT')
    parser.add_argument('--output', type=str, default='summary.html',
                        help='default output filename (default: %(default)s).'
                             'file is output as "ROOT/OUTPUT"')
    parser.add_argument('--viewerjs', default=False,
                        action='store_true',
                        help='enable ViewerJS PDF viewer')

    args = parser.parse_args()

    rootpath = pathlib.Path(args.root)
    if rootpath.is_file():
        rootpath = rootpath.parent

    outputpath = rootpath / args.output

    # rootpathの名前をタイトルにする
    assignmentname = rootpath.absolute().name

    with outputpath.open('wb') as output_buffer:
        main(output_buffer, root=rootpath, assignmentname=assignmentname,
             enable_viewerjs=args.viewerjs)
