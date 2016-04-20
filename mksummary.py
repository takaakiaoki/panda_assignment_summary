import pathlib
import pytz
import datetime
import urllib
import re
import io
import sys
import argparse

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


def foreachpersonaldir(d):
    """個人フォルダの中をパースし, 必要な情報を取り出す
    timestamp.txt がなければ None を返す

    {timestamp: DateTimeObject,
     attachments: [relative path, pathlib.Path object]}
    """

    obj = {'timezone': None,
           'attachments': []}

    tpath = d / 'timestamp.txt'
    if tpath.exists():
        tstext = tpath.read_text()
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

    return None



def load_id_group_mapping(path, encoding='cp932'):
    """ファイルを読み込み, 学籍番号とグループ, グループ内番号のマップを作る
       ファイルは, 1行目がヘッダ, 以降
           ID	姓	名	班	番号	採点グループ	採点グループ番号	
       とタブ区切り
    path は pathlib.Path オブジェクト
    encoding はファイルの文字コード(たいていcp932 か utf8)
    """

    idlist = []

    with path.open(encoding=encoding) as f:
        # 一行スキップ
        next(f)
        for line in f.readlines():
            # タブでパース
            sps = line.split('\t')
            idlist.append({
                'id': sps[0],
                'surname': sps[1],
                'givenname': sps[2],
                'group': int(sps[3]),
                'n_in_group': int(sps[4]),
                'asses_grp': sps[5],
                'n_in_agrp': int(sps[6])})

    return idlist

def create_contents(root=pathlib.Path('.')):
    """パス上のフォルダを検索し, {"id":"htmlコンテンツ"}のマップを作る
    root は検索パス
    """

    id_contents_map = {}

    dirs = root.glob('*,(*)')
    for d in dirs:
        # () 内のIDを取り出す.
        reobj = re.compile(u'.+,\((?P<id>[0-9x]+)\)')
        mobj = reobj.match(d.name)
        if mobj:
            # フォルダの中をパースする.
            id_contents_map[mobj.group('id')] = foreachpersonaldir(d)

    return id_contents_map



def main(output_buffer, idlistpath, html_output_encoding='utf-8'):
    """
    Args:
        output (File): binary IO to output
        idlistpath (pathlib.Path): path object to read id-sequence data
    """

    idlist = load_id_group_mapping(idlistpath, encoding='cp932')

    id_contents_map = create_contents()

    writer = io.TextIOWrapper(output_buffer, encoding=html_output_encoding, newline='\n')
    
    group = 0
    print('<!DOCTYPE html>\n', file=writer)
    print('<html>\n', file=writer)
    print('  <meta charset="{0:s}">'.format(html_output_encoding), file=writer)
    print('<body>', file=writer)

    # 各班へのリンク
    print('<a name="top"></a>', file=writer)
    groups = [list(range(1, 7)),
              list(range(7, 7*2)),
              list(range(7*2, 7*3)),
              list(range(7*3, 7*4)),
              list(range(7*4, 7*5)),
              [40, 41]]
            
    for gg in groups:
        for g in gg:
            print('<a href="#group{0:d}">{0:d}班</a>, '.format(g), end='', file=writer)
        print('<br/>', file=writer)

    for p in idlist:
        # 新しい班?
        if p['group'] != group:
            group = p['group']
            print('<hr><hr><h2 id="group{0:d}">{0:d}班</h2>'.format(group), file=writer)
            print('<span size="-2"><a href="#top">Top</a></span>', file=writer)

        # 氏名を表示
        print('<hr><h3>{0:s} {1:s}</h3>'.format(p['surname'], p['givenname']), file=writer)
        
        # コンテンツを確認
        c = id_contents_map.get(p['id'], None)
        if c is None:
            print('提出未確認<br/>', file=writer)
        else:
            # タイムスタンプ
            print('timestamp: {0:s}<br/>'.format(str(c['timestamp'])), file=writer)
            # 添付ファイル
            print('attachments:<br/>', file=writer)
            for a in c['attachments']:
                # リンクパスをurl形式に変換
                relurl = urllib.parse.urlunsplit(('', '', str(a.as_posix()), '', ''))
                # in sake for working on IE11 and Edge (and other browsers)
                # do not escape multibyte URL
                # linkurl = urllib.parse.quote(relurl)
                linkurl = relurl
                print('<a href="{0:s}">'.format(linkurl), end='', file=writer)
                if a.suffix.lower() in ('.png', '.jpg', '.jpeg'):
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

    args = parser.parse_args()

    with open(args.output, 'wb') as output_buffer:
        idlistpath = pathlib.Path('ID-group-map.txt')
        main(output_buffer, idlistpath)
