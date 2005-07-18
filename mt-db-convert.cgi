#!/usr/bin/perl -w
# mt-db-convert.cgi: converting your MT data between multiple db engines
# This is a derived work from the following:
#
# Copyright 2001-2005 Six Apart. This code cannot be redistributed without
# permission from www.movabletype.org.
#
# $Id: mt-db2sql.cgi 12446 2005-05-25 21:32:39Z bchoate $
use strict;

my $VERSION = '0.12';

my($MT_DIR);
BEGIN {
    if ($0 =~ m!(.*[/\\])!) {
        $MT_DIR = $1;
    } else {
        $MT_DIR = './';
    }
    unshift @INC, $MT_DIR . 'lib';
    unshift @INC, $MT_DIR . 'extlib';
}

local $| = 1;
print "Content-Type: text/html\n\n";
print <<HTML;
<html>
<head><title>mt-db-convert $VERSION: Converting your MT data</title></head>
<body>
<p><strong>mt-db-convert $VERSION: Coverting your MT data between DB engines</strong></p>
HTML

my @CLASSES = qw( MT::Author MT::Blog MT::Category MT::Comment MT::Entry
                  MT::IPBanList MT::Log MT::Notification MT::Permission
                  MT::Placement MT::Template MT::TemplateMap MT::Trackback
                  MT::TBPing );

use File::Spec;

my @DBSPECS = qw( DataSource ObjectDriver Database DBUser DBHost DBPassword );

require MT;
my $mt = MT->new(Config => $MT_DIR . 'mt.cfg', Directory => $MT_DIR)
    or die MT->errstr;
my $cfg = $mt->{cfg};

use CGI;
my $q = CGI->new;

my (%src, %dst);
foreach (@DBSPECS) {
    $src{$_} = $q->param('src_' . $_) || '';
    $dst{$_} = $q->param('dst_' . $_) || '';
}

# If src and dst dbspecs not given
if (!$src{ObjectDriver} || ($src{ObjectDriver} eq 'DBM' && !$src{DataSource}) ||
    !$dst{ObjectDriver} || ($dst{ObjectDriver} eq 'DBM' && !$dst{DataSource})) {

    $src{$_} ||= $cfg->$_() foreach (@DBSPECS);

    my %src_selected = ('DBM' => '', 'DBI::mysql' => '', 'DBI::postgres' => '', 'DBI::sqlite' => '');
    my %dst_selected = ('DBM' => '', 'DBI::mysql' => '', 'DBI::postgres' => '', 'DBI::sqlite' => '');
    $src_selected{$src{ObjectDriver}} = 'selected' if $src{ObjectDriver};
    $dst_selected{$dst{ObjectDriver}} = 'selected' if $dst{ObjectDriver};

    my $script_name = ($0 =~ m![/\\]([^/\\]+)$!) ? $1 : 'mt-db-convert.cgi';

    print <<HTML;
<p>Please fill the following:</p>

<form method="post" action="$script_name">
<style>fieldset { width: 40%; float: left; }</style>
<fieldset>
<legend>Source DB Configuration</legend>
<dl>
<dt>DataSource: (Required for BerkeleyDB)</dt>
<dd><input name="src_DataSource" type="text" value="$src{DataSource}" /></dd>
<dt>ObjectDriver:</dt>
<dd><select name="src_ObjectDriver">
<option value="">Select a driver</option>
<option value="DBM" $src_selected{'DBM'}>BerkeleyDB</option>
<option value="DBI::mysql" $src_selected{'DBI::mysql'}>MySQL</option>
<option value="DBI::postgres" $src_selected{'DBI::postgres'}>PostgreSQL</option>
<option value="DBI::sqlite" $src_selected{'DBI::sqlite'}>SQLite</option>
</select></dd>
<dt>Database:</dt>
<dd><input name="src_Database" type="text" value="$src{Database}" /></dd>
<dt>DBUser:</dt>
<dd><input name="src_DBUser" type="text" value="$src{DBUser}" /></dd>
<dt>DBHost:</dt>
<dd><input name="src_DBHost" type="text" value="$src{DBHost}" /></dd>
<dt>DBPassword:</dt>
<dd><input name="src_DBPassword" type="password" value="" /></dd>
</dl>
</fieldset>

<fieldset>
<legend>Destination DB Configuration</legend>
<dl>
<dt>DataSource: (Required for BerkeleyDB)</dt>
<dd><input name="dst_DataSource" type="text" value="$dst{DataSource}" /></dd>
<dt>ObjectDriver:</dt>
<dd><select name="dst_ObjectDriver">
<option value="">Select a driver</option>
<option value="DBM" $dst_selected{'DBM'}>BerkeleyDB</option>
<option value="DBI::mysql" $dst_selected{'DBI::mysql'}>MySQL</option>
<option value="DBI::postgres" $dst_selected{'DBI::postgres'}>PostgreSQL</option>
<option value="DBI::sqlite" $dst_selected{'DBI::sqlite'}>SQLite</option>
</select></dd>
<dt>Database:</dt>
<dd><input name="dst_Database" type="text" value="$dst{Database}" /></dd>
<dt>DBUser:</dt>
<dd><input name="dst_DBUser" type="text" value="$dst{DBUser}" /></dd>
<dt>DBHost:</dt>
<dd><input name="dst_DBHost" type="text" value="$dst{DBHost}" /></dd>
<dt>DBPassword:</dt>
<dd><input name="dst_DBPassword" type="password" value="$dst{DBPassword}" /></dd>
</dl>
</fieldset>

<p style="clear:both;"><input type="submit" value="Convert" /></p>
</form>
HTML

} else {

eval {
    local $SIG{__WARN__} = sub { print "**** WARNING: $_[0]\n" };

    require MT::Object;
    my $type = ($dst{ObjectDriver} =~ /^DBI::(.*)$/) ? $1 : '';
    if ($type) {
    # set dst driver
    $cfg->set($_, $dst{$_}) foreach (@DBSPECS);
    MT::Object->set_driver($dst{ObjectDriver})
        or die MT::ObjectDriver->errstr;
    my $dbh = MT::Object->driver->{dbh};
    $dbh->begin_work if $type eq 'sqlite';
    my $schema = File::Spec->catfile($MT_DIR, 'schemas', $type . '.dump');
    open FH, $schema or die "Can't open schema file '$schema': $!";
    my $ddl;
    { local $/; $ddl = <FH> }
    close FH;
    my @stmts = split /;/, $ddl;
    print "<p>Loading database schema...</p>\n\n";
    for my $stmt (@stmts) {
        $stmt =~ s!^\s*!!;
        $stmt =~ s!\s*$!!;
        next unless $stmt =~ /\S/;
        $dbh->do($stmt) or die $dbh->errstr;
    }
    $dbh->commit if $type eq 'sqlite';
    }

    ## %ids will hold the highest IDs of each class.
    my %ids;

    for my $class (@CLASSES) {
	print "<p>Dumping $class:<br />\n";

	# set source driver
	$cfg->set($_, $src{$_}) foreach (@DBSPECS);
	MT::Object->set_driver($src{ObjectDriver});

        eval "use $class";
        my $iter = $class->load_iter;

        my %names;
        my %cat_parent;

	# set dst driver
	$cfg->set($_, $dst{$_}) foreach (@DBSPECS);
	MT::Object->set_driver($dst{ObjectDriver});
	MT::Object->driver->{dbh}->begin_work if $type eq 'sqlite';

	my $i = 0;
        while (my $obj = $iter->()) {
            $ids{$class} = $obj->id
                if !$ids{$class} || $obj->id > $ids{$class};
            ## Look for duplicate template, category, and author names,
            ## because we have uniqueness constraints in the DB.
            if ($class eq 'MT::Template') {
                my $key = lc($obj->name) . $obj->blog_id;
                if ($names{$class}{$key}++) {
                    print "        Found duplicate template name '" .
                          $obj->name;
                    $obj->name($obj->name . ' ' . $names{$class}{$key});
                    print "'; renaming to '" . $obj->name . "'\n";
                }
                ## Touch the text column to make sure we read in
                ## any linked templates.
                my $text = $obj->text;
            } elsif ($class eq 'MT::Author') {
                my $key = lc($obj->name);
                if ($names{$class . $obj->type}{$key}++) {
                    print "        Found duplicate author name '" .
                          $obj->name;
                    $obj->name($obj->name . ' ' . $names{$class}{$key});
                    print "'; renaming to '" . $obj->name . "'\n";
                }
                $obj->email('') unless defined $obj->email;
                $obj->set_password('') unless defined $obj->password;
            } elsif ($class eq 'MT::Category') {
                my $key = lc($obj->label) . $obj->blog_id;
                if ($names{$class}{$key}++) {
                    print "        Found duplicate category label '" .
                          $obj->label;
                    $obj->label($obj->label . ' ' . $names{$class}{$key});
                    print "'; renaming to '" . $obj->label . "'\n";
                }
                # save the parent value for assignment at the end
                if ($obj->parent) {
                    $cat_parent{$obj->id} = $obj->parent;
                    $obj->parent(0);
                }
            } elsif ($class eq 'MT::Trackback') {
                $obj->entry_id(0) unless defined $obj->entry_id;
                $obj->category_id(0) unless defined $obj->category_id;
            } elsif ($class eq 'MT::Entry') {
                $obj->allow_pings(0)
                    if defined $obj->allow_pings && $obj->allow_pings eq '';
                $obj->allow_comments(0)
                    if defined $obj->allow_comments && $obj->allow_comments eq '';
            } elsif ($class eq 'MT::Blog') {
		$obj->touch(); # for updating children_modified_on field
            }

	    $i++;
            $obj->save
                or die $obj->errstr;
	    print ".";
	    $i % 10 or print " ";
	    $i % 100 or print "<br />\n";
        }

        # fix up the category parents
        foreach my $id (keys %cat_parent) {
            my $cat = MT::Category->load($id);
            $cat->parent( $cat_parent{$id} );
            $cat->save;
        }

	print "</p>\n\n";
	MT::Object->driver->{dbh}->commit if $type eq 'sqlite';
    }

    if ($type eq 'postgres') {
        print "Updating sequences\n";
        my $dbh = MT::Object->driver->{dbh};
        for my $class (keys %ids) {
            print "    $class => $ids{$class}\n";
            my $seq = 'mt_' . $class->datasource . '_' .
                      $class->properties->{primary_key};
            $dbh->do("select setval('$seq', $ids{$class})")
                or die $dbh->errstr;
        }
    }
};
if ($@) {
    print <<HTML;
<p>An error occurred while loading data: <br />
$@</p>
HTML
} else {
    print <<HTML;
<p>Done copying data from $src{ObjectDriver} to $dst{ObjectDriver}! All went well.</p>
HTML
}

}

print "</body>\n</html>\n";
