##########################
panda_assignment mksummary
##########################

PandA(Sakai) でダウンロードした課題ファイルは,
ユーザー毎に分類されたフォルダに格納されるため,
手早くプレビューすることが困難です.

mksummary.py (mksummary.exe) は個々のフォルダを巡回し, 

* 提出者氏名
* タイムスタンプの内容
* html形式テキストの内容
* 添付として提出されたファイルの内, 画像ファイルならば画像の埋め込み, それ以外ならば当該ファイルへのリンク

を一つのhtmlファイルとして生成します.

利用方法
========

windowsの場合, mksummary.exe を入手してください.
この実行ファイルをPandAの提出物個人フォルダと同じレベルに配置します.
mksummary.exe を実行すると summary.html が作製されます.

PandA(Sakai)の提出物は次のような構成をとります.

::

   bulk_download.zip
     + 課題名/
       + 学生氏名, (学生証番号)/
         + 学生氏名, (学生証番号)_submission_text.html
         + timestamp.txt
         + 提出物の添付/
           + 添付ファイル1
           + 添付ファイル2
           :
       + 学生氏名, (学生証番号)/
       + 学生氏名, (学生証番号)/
       + 学生氏名, (学生証番号)/
       :
       + mksummary.exe  <-- ここに配置します
       + summary.html <-- このファイルが生成されます.

Mac, Unix の場合, mksummary.exe の代わりに mksummary.py を配置し, これを実行します. 

* python のバージョンは, 3.4 または 3.5 で動作確認をしています.
* mksummary.py に必要は標準以外のモジュールは以下の通りです. PyPIから入手できます.
  - pytz  (pip install pytz)

開発者向け情報
==============

.py から .exe の生成は PyInstaller (http://www.pyinstaller.org/) を使用しています.

  pip install pyinstaller
 
でインストール(同時に pypiwin32 のインストールされます),

  pyinstaller --onefile mksummary.py

で実行ファイルが dist ディレクトリの下に生成されます.
pythonが空白を含むパスにインストールされている場合, 'failed to create process' のエラーにより動かない場合があります.

http://stackoverflow.com/questions/31808180/installing-pyinstaller-via-pip-leads-to-failed-to-create-process

に従って, pyinstaller 関連のスクリプトの1行目にクオーテーションマークを入れてください.
