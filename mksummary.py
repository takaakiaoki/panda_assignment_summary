import pathlib
import pytz
import datetime
import urllib
import re
import io
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
            obj['attachments'].append(f)

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
            dirpath = root / (sps[1] + ' ' + sps[2] + ',(' + sps[0] + ')')

            if dirpath.is_dir():
                obj['personaldir'] = foreachpersonaldir(dirpath)

            yield obj


def render_personalfolder(p, writer, enable_viewerjs=False):
    """ foreachpersonaldir の内容を html で出力する.
    Args:
        p (dict): foreachpersonaldir の結果
        writer (File): htmlの出力対象
        enable_viwerjs (bool): ViewerJS でのプレビューに対応する.
    """
    # タイムスタンプでコンテンツを確認
    if p['timestamp'] is None:
        print('提出未確認<br/>', file=writer)
    else:
        # タイムスタンプ
        print('timestamp: {0:s}<br/>'.format(str(p['timestamp'])), file=writer)
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
                    print('<iframe class="attacheddoc" src="_summary/ViewerJS/#../../{0:s}" allowfullscreen webkitallowfullscreen></iframe>'.format(linkurl),
                          end='', file=writer)
                else:
                    print('{0:s}</a><br/>'.format(linkurl), file=writer)


def main(output_buffer, root=pathlib.Path('.'),
         html_output_encoding='utf-8',
         enable_viewerjs='False'):
    """
    Args:
        output_buffer (File): binary IO to output
        root (pathlib.Path): root path to walk
        html_output_encoding (str): encoding for output html
        enable_viwerjs (bool): ViewerJS でのプレビューに対応する.
    """

    idlist = pathlib.Path('ID-group-map.txt')

    writer = io.TextIOWrapper(output_buffer, encoding=html_output_encoding, newline='\n')

    print('<!DOCTYPE html>', file=writer)
    print('<html>', file=writer)
    print('<head>', file=writer)
    print('\t<meta charset="{0:s}">'.format(html_output_encoding), file=writer)
    print('\t<style type="text/css">', file=writer)
    print('''div.submissionText {
	background: #f0f0f0;
	border: medium solid #0f0f0f;
	font-size: smaller;
	margin: 0 auto;
	width: 90%;
}
img.attachedimg {
    width: 510px;
}
iframe.attacheddoc {
    width: 510px;
    height: 720px;
}
''', file=writer)
    print('\t</style>', file=writer)
    print('</head>', file=writer)
    print('<body>', file=writer)

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

    group = 0
    for p in walk_personal_dirs_idlist(idlist, root):
        # 新しい班?
        if p['group'] != group:
            group = p['group']
            print('<hr><hr><h2 id="group{0:d}">{0:d}班</h2>'.format(group), file=writer)
            print('<span size="-2"><a href="#top">Top</a></span>', file=writer)

        # 氏名を表示
        print('<hr><h3>{0:s} {1:s}</h3>'.format(p['surname'], p['givenname']), file=writer)

        # コンテンツを確認
        c = p['personaldir']
        if c is None:
            print('フォルダが確認できません<br/>', file=writer)
        else:
            render_personalfolder(c, writer, enable_viewerjs)

    print('</body></html>', file=writer)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('output', nargs='?', type=str, default='summary.html',
                        help='default output filename (default: %(default)s)')
    parser.add_argument('--root', type=str, default='.',
                        help='root directory (default: %(default)s)')
    parser.add_argument('--viewerjs', default=False,
                        action='store_true',
                        help='enable ViewerJS PDF viewer')

    args = parser.parse_args()

    with open(args.output, 'wb') as output_buffer:
        main(output_buffer, root=pathlib.Path(args.root),
             enable_viewerjs=args.viewerjs)
