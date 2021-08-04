##########################
panda_assignment_mksummary
##########################

English instruction: `README-e.rst <https://github.com/takaakiaoki/panda_assignment_summary/blob/master/README-e.rst>`_

お断り
======

.. warning::
  
  このリポジトリの内容は, 京都大学の `Code for PandA <//www.iimc.kyoto-u.ac.jp/ja/services/lms/>`_ の対象ではありません.
  
  また, 作成者の異動に伴い, 最新のPandAの形式に適合していない可能性があります.

このソフトウェアについて
==========================

PandA(Sakai) でダウンロードした課題ファイルは,
ユーザー毎に分類されたフォルダに格納されるため,
手早くプレビューすることが困難です.

mksummary.py (mksummary.exe) は個々のフォルダを巡回し, 

* 提出者氏名
* タイムスタンプの内容
* html形式テキストの内容
* 添付として提出されたファイルの内, 画像ファイルならば画像の埋め込み, それ以外ならば当該ファイルへのリンク

を一つのhtmlファイルとして生成します.


利用方法(Windows)
========================

1. windowsの場合, mksummary.exe (https://github.com/takaakiaoki/panda_assignment_summary/releases) を入手してください.
   この実行ファイルをデスクトップに配置します.

2. PandA(Sakai)の提出物は以下のような構成をとります. ここで 

   * 「課題名」のフォルダ
   * 「grades.csv」等の「課題名」フォルダの中にある **ファイル**

   を選び, 1. のプログラム上にドラッグ&ドロップします. 「課題名」フォルダの中に「summary.html」ファイルが作成されます.

   ::

      bulk_download.zip
        - 課題名/        <-- このフォルダ または
          - grades.csv   <-- このファイルをプログラム上にD&D
          - 学生氏名, (学生証番号)/
            - 学生氏名, (学生証番号)_submission_text.html
            - timestamp.txt
            - 提出物の添付/
              - 添付ファイル1
              - 添付ファイル2
              :
          - 学生氏名, (学生証番号)/
          - 学生氏名, (学生証番号)/
          - 学生氏名, (学生証番号)/
          :
          - summary.html <-- このファイルが生成されます.

3. summary.html をブラウザで開くと提出物の内容が閲覧できます.
   
   また, 個人毎の項目に設けられた「点数」のフォームに点数を記入することができます. ページトップの「採点表」ボタンを押すと, 一覧表が別ウインドウで作成されます.
   これを grades.csv (または grades.xlsx) にコピー&ペーストし, PandAにアップロードすることができます.


その他の利用方法
========================

Mac, Unix (+windows) では, pythonを事前に準備した後, mksummary.py を配置し, これを実行します. 

::

   「課題名」フォルダの中において

   > mksummary.py

または, 第1引数に課題名フォルダを指定します.

::

   > mksummary.py 課題フォルダ名


* python のバージョンは, 3.4 または 3.5 で動作確認をしています. 
* mksummary.py に必要な標準以外のモジュールは以下の通りです. PyPIから入手できます.

  - pytz  (pip install pytz)


ViewerJS を用いPDFファイルをプレビューする
==========================================

ViewrJS (http://viewerjs.org/) を用いることで PDF, ODF ファイルのプレビューを埋め込むことができます.
ただし, 以下の準備が必要です.

.. note::

   javascript は原則としてローカルファイルへのアクセスを禁止します.
   このため, 手元のPC内にhttpサーバーを立て, サーバー-クライアントとして動作させます.

0. python をインストールします. 
1. ViewerJS を入手します (http://viewerjs.org/releases/ViewerJS-latest.zip をダウンロード)
2. このファイルを展開し, 以下のように配置します.

   ::

      bulk_download.zip
        - 課題名/
          - 学生氏名, (学生証番号)/
            - 学生氏名, (学生証番号)_submission_text.html
            - timestamp.txt
            - 提出物の添付/
              - 添付ファイル1
              - 添付ファイル2
              :
          - 学生氏名 (学生証番号)/
          - 学生氏名 (学生証番号)/
          - 学生氏名 (学生証番号)/
          :
          - summary.html 
          - _summary/ <-- このフォルダを作成します
            - ViewerJS/ <-- 展開した ViewerJS フォルダをここにコピーします
              - images/
              - compatibility.js
              - example.local.css
              :

3. mksummary.exe または mksummary.py を :option:`viewerjs` オプション付きで実行します. コマンドプロンプトを開き

      mksummary.exe [課題フォルダ名] --viewerjs
   
   または

      python mksummary.py [課題フォルダ名] --viewerjs

4. httpサーバーを立ち上げます. Python にはシンプルなhttpサーバーモジュールが付属しているのでこれを利用します.

      python -m http.server

5. ブラウザを開き, http://localhost:8000/summary.html にアクセスします.


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


ライセンス
==========

このソフトウェアはMITライセンスの下で公開しています. ライセンスの詳細は LISENCE.txt をご参照ください.
