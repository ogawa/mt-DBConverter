# MT Database Converter

A CGI script for converting Movable Type Database between DB engines.

## Changes

 * 0.11 (2005.07.16):
   * Initial release.
 * 0.12 (2005.07.18):
   * Bug fix for using BerkeleyDB.

## Overview

This script allows you to mutually convert Movable Type Data between BerkeleyDB, MySQL, PostgreSQL, and SQLite. When you want to move your database from MySQL to SQLite, or move from a testing environment to a production, this script can help you.

This script is a kind of a derived work of Six Apart's mt-db2sql.cgi. So I may cease publishing this article and this script anytime as requested.

## Installation

To install this script, upload or copy "mt-db-convert.cgi" into your Movable Type directory and set the permission of the script to 0755 (be executable).

To use it, just acccess it with your Web browser.

''(I have to write more about how to use this.)''

After running this script, I strongly recommend to delete it, because it becomes a security hole of your MT. I mean anybody else could access it and read your DB configuration.

## Note

 * This script is compatible with Movable Type version 3.1x.  I didn't test it at any other versions.
 * This script may be stopped publishing anytime at Six Apart's request.

## See Also

 * 
