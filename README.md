# MT Database Converter

Movable TypeのデータベースをDB間で相互にコンバートするCGIスクリプト。

## 更新履歴

 * 0.10 (2005.03.??):
   * 作成。
 * 0.11 (2005.07.16):
   * サブカテゴリーをコンバートする際の問題を解決(したつもり)。
   * Movable Type 3.1以降でMT::Blogオブジェクトをコンバートする際の問題を解決。
   * 公開開始。
 * 0.12 (2005.07.18):
   * BerkeleyDB周りのバグを修正。
 * 0.14 (2005.10.09):
   * Movable Type 3.2への対応。
   * バージョンチェックの追加。
   * 変換後に設定用のヒント情報を表示するように若干出力内容を変更。
 * 0.20 (2006.01.13):
   * ユーザインタフェースの改善(必要な項目のみを入力できるようにJavascriptでちょっとお化粧しました)。
   * コンバート後トラックバックがなくなってしまうバグの修正。
 * 0.30 (2006.07.17):
   * Movable Type 3.3への対応。
   * バージョンチェックを少し厳密に検査するようにした。

## 概要

Movable TypeのデータベースをBerkeleyDB、MySQL、PostgreSQL、SQLiteの間で相互に変換するCGIスクリプトです。テスト環境から本番環境への移行、プラグインの開発、そしてDBのアップグレードなど、データベースを一方から他方に移行したい場合に役に立ちます。DB間の相互変換は、従来からMovable Typeに付属しているmt-db2sql.cgiと拙作の[mt-sql2db.cgi](http://blog.as-is.net/2004/08/mt-sql2dbcgi-mt-db2sqlcgi-cgi.html)を組み合わせれば実現できましたが、このスクリプトはそれを単体で実現します。また、mt-sql2db.cgiにあったバグをいくつか修正してあります。

## インストール方法

mt-db-convert.zipに含まれる、

 * mt-db-convert31.cgi: Movable Type 3.1用
 * mt-db-convert32.cgi: Movable Type 3.2用
 * mt-db-convert33.cgi: Movable Type 3.3用

のうちいずれか一つ選び(以降、選んだものをmt-db-convert.cgiと記載します。利用しているMovable Typeのバージョンに合わせて読み替えてください。)、mt.cgiなどと同じディレクトリにコピーし、実行パーミッションを設定します。

## 使用方法

使用に先立って転送元のDBのバックアップを取っておくこと、使用後はmt-db-convert.cgiを削除しておくことをお忘れなく。

mt-db-convert.cgiでは、mt-db2sql.cgiとは異なり、あらかじめmt-config.cgiないしmt.cfgの書き換えは必要ありません。変換後に修正してください。

 1. Webブラウザでmt-db-convert.cgiにアクセスします。
 1. 「Source DB Configuration」に転送元の情報を入力します。簡便のため、デフォルトでmt-config.cgiないしmt.cfgの情報が設定されています(安全のためDBPasswordは設定されません)。必要に応じて書き換えてください。
 1. 「Destination DB Configuration」に転送先の情報を入力します。BerkeleyDBの場合にはDataSourceの入力、それ以外の場合にはDataBaseなどの入力が必要になります。BerkeleyDBのDataSourceはフルパスで入力することをお勧めします。SQLiteのDatabaseもフルパスで入力することをお勧めします。
 1. 「Convert」ボタンをクリックすると、転送元から転送先にDBの変換が行われます。
 1. 無事変換が終了すると、以下のようにmt-config.cgiを設定し直すのに参考になるヒント情報が表示されます。これを参考に適宜修正してください。

     Your recommended setting
     \# DataSource /home/ogawa/public_html/mt/db
     ObjectDriver DBI::sqlite
     Database /home/ogawa/public_html/mt/mt_sqlite.db

## SQLiteに関するチューニング

mt-db-convert.cgiは、SQLiteのトランザクション機能を利用したチューニングを行っています。このため、出力先DBをSQLiteにした場合、mt-db2sql.cgiを使用するのに比べて大幅な高速化が期待できます。参考までに、私の手元の環境では、BerkeleyDBからSQLiteへの変換が93秒から25秒に短縮されました。

つまり、レンタルサーバーなどではタイムアウトで500 Internal Server Errorになりがちなmt-db2sql.cgiの代用としても使用することができます。

## 注意事項

 * コンバート後に受信済みのトラックバックを参照できない症状が生じた場合には、[DBコンバート後に受信済みのトラックバックを参照できない問題への対処](http://blog.as-is.net/2006/01/db.html)を参照してください。なお現在配布しているバージョンではこの問題に対処してあります。
 * MT 3.1xと3.2でしか動作確認をしていません。
 * レンタルサーバーなどでは500 Internal Server Errorが出ることがあります。この場合は転送先DBを削除し、時間をおいて再度試みてください。何度やっても無理な場合にはあきらめてください。
 * 求めに応じて公開を停止する場合があります。

== See Also ==

 *
