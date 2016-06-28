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


def walk_personal_dirs_idlist(idlist, root=pathlib.Path('.')):
    """パス上のフォルダを検索し, foreachpersondir のコンテンツをiterativeに取得する.

    Args:
        idlist (pathlib.Path): 学籍番号, 氏, 名, 班, 班内番号, (あとは任意)のリスト
            1行目はヘッダファイル, カラムはタブ区切り, 以下は例
                ID	姓	名	班	番号	採点グループ	採点グループ番
                1235467980	京大	太郎	1	1	a	1
                3124657818	吉田	花子	1	2	a	2
                1423576792	二本松	一郎	2	1	a	3
                1253468693	桂	さくら	2	4	a	4
        root (pathlib.Path): 検索開始パス

    Yields: dict object connecting row data and result from foreachpersonaldir
        {
            id: str          # 1st column of idlist
            surname: str     # 2nd
            givenname: str   # 3rd
            group: int       # 4th
            n_in_group: int  # 5th
            personaldir: None or (result from foreachpersonaldir)
        }
    """

    with idlist.open('rt') as f:
        # skip header
        next(f)
        for line in f.readlines():
            # タブでパース
            sps = line.split('\t')
            # 個人フォルダを構成
            obj = {'id': sps[0],
                   'surname': sps[1],
                   'givenname': sps[2],
                   'group': int(sps[3]),
                   'n_in_group': int(sps[4]),
                   'personaldir': None}

            # フォルダは root からの相対値
            # 5/21 以降のフォーマット
            dirpath = root / (sps[1] + ' ' + sps[2] + ' (' + sps[0] + ')')
            if dirpath.is_dir():
                obj['personaldir'] = foreachpersonaldir(dirpath, root)
            else:
                # 5/21 以前のフォーマット
                dirpath = root / (sps[1] + ' ' + sps[2] + ',(' + sps[0] + ')')
                if dirpath.is_dir():
                    obj['personaldir'] = foreachpersonaldir(dirpath, root)

            yield obj


def render_personalfolder(p,
                          writer,
                          enable_viewerjs=False,
                          scorefield=None,
                          commentfield=None):
    """ foreachpersonaldir の内容を html で出力する.
    Args:
        p (dict): foreachpersonaldir の結果. None の場合, 'フォルダが確認できません' を出力
        writer (File): htmlの出力対象
        enable_viwerjs (optional[bool]): ViewerJS でのプレビューに対応する.
        scorefield (optional[dict]): 得点フォームの情報, Noneの場合不要
            score (int): 現在の点数, None だとデフォルト値を採用
            fullscore (int): 満点
            formname (str): このフォームの name 属性
        commentfield (optional[dict]): コメントフォームの情報, Noneの場合不要
            formname (str): このフォームの name 属性
            [data (str)]: テキストデータ
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

    def formatcommentform(c):
        '''コメントフォームをフォーマットする

        Args:
            c (dict): コメントフォームの情報
                formname (str): このフォームの name 属性
                [data (str)]: テキストデータ
        '''
        return '<textarea name="{0:s}" rows="3" cols="40">{1:s}</textarea><br>'.format(commentfield['formname'], commentfield.get('data', ''))

    def printforms(writer, scorefield=None, defaultscore=0, commentfield=None):
        '''点数フォーム, コメントフォームをフォーマット,  出力する

        Args:
            writer (File): htmlの出力対象
            scorefield (optional[dict]): 得点フォームの情報, Noneの場合不要
                score (int): 現在の点数, None だとデフォルト値を採用
                fullscore (int): 満点
                formname (str): このフォームの name 属性
            defaultscore: scorefield['score'] == None の場合に適用する点数
            commentfield (optional[dict]): コメントフォームの情報, Noneの場合不要
                formname (str): このフォームの name 属性
                [data (str)]: テキストデータ
        '''
        if scorefield:
            print(formatscoreform(scorefield, defaultscore), file=writer)
        if commentfield:
            print('コメント(comment):<br>', file=writer)
            print(formatcommentform(commentfield), file=writer)

    if p is None:
        # 点数・コメントフィールド (デフォルトは 減点法なので20)
        printforms(writer, scorefield, 20, commentfield)
        print('フォルダがありません(personal folder is not found)<br>', file=writer)
        return

    # タイムスタンプでコンテンツを確認
    if p['timestamp'] is None:
        # 点数・コメントフィールド (デフォルトは 減点法なので20)
        printforms(writer, scorefield, 20, commentfield)
        print('提出未確認(materials not found)<br>', file=writer)
        return

    # 有効なコンテンツ
    # 点数・コメントフィールド (デフォルトは 減点法なので0)
    printforms(writer, scorefield, 0, commentfield)
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
page.document.write("<tr><th>班</th><th>ID</th><th>氏名(Name)</th><th>点数(score)</th><th>コメント(comment)</th></tr>");
''', file=writer)

    # 履修者の個々の表，form の値を参照してつくる
    # 点数は form2 の 's'+(id), コメントは 'c'+(id)
    for p in personal_dirs:
        print('page.document.write("<tr><td>{0:d}</td>")'.format(p['group']), file=writer)
        print('page.document.write("<td>{0:s}</td>")'.format(p['id']), file=writer)
        print('page.document.write("<td>{0:s} {1:s}</td>")'.format(p['surname'], p['givenname']), file=writer)
        print('page.document.write("<td>",document.form2.{0:s}.value,"</td>")'.format('s'+p['id']),file=writer)
        print('page.document.write("<td>",document.form2.{0:s}.value,"</td></tr>")'.format('c'+p['id']),file=writer)

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

    idlist = root / 'ID-group-map.txt'

    writer = io.TextIOWrapper(output_buffer, encoding=html_output_encoding, newline='\n')

    # フォルダを巡回し, コンテンツのリストを作る.
    personal_dirs = list(walk_personal_dirs_idlist(idlist, root))

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

    print('<hr>', file=writer)

    # 各班へのリンク
    groups = [list(range(1, 7)),
              list(range(7, 7*2)),
              list(range(7*2, 7*3)),
              list(range(7*3, 7*4)),
              list(range(7*4, 7*5)),
              [40, 41]]

    print('<nav><a name="top"></a>', file=writer)
    for gg in groups:
        for g in gg:
            print('<a href="#group{0:d}">{0:d}班</a>, '.format(g), end='', file=writer)
        print('<br/>', file=writer)
    print('</nav>', file=writer)

    print('<form name="form2">', file=writer)
    group = 0
    for p in personal_dirs:
        # 新しい班?
        if p['group'] != group:
            group = p['group']
            print('<hr><hr><h2 id="group{0:d}">{0:d}班</h2>'.format(group), file=writer)
            print('<span size="-2"><a href="#top">Top</a></span>', file=writer)

        # 氏名を表示
        print('<hr><h3>{0:s} {1:s}</h3>'.format(p['surname'], p['givenname']), file=writer)

        # 採点用フォームデータ
        scorefield = {
            'formname': 's' + p['id'],
            'score': None,
            'fullscore': 20}
        commentfield = {
            'formname': 'c' + p['id']}
        render_personalfolder(p['personaldir'], writer,
                              enable_viewerjs=enable_viewerjs,
                              scorefield=scorefield,
                              commentfield=commentfield)

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
