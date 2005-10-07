#!/usr/bin/perl -w
# mt-db-convert.cgi: converting your MT data between multiple db engines
# This is a derived work from the following:

# Copyright 2001-2005 Six Apart. This code cannot be redistributed without
# permission from www.sixapart.com.  For more information, consult your
# Movable Type license.
#
# $Id: mt-db2sql.cgi 15432 2005-07-29 20:41:11Z bchoate $

use strict;
sub BEGIN {
    my $dir;
    require File::Spec;
    if (!($dir = $ENV{MT_HOME})) {
        if ($0 =~ m!(.*[/\\])!) {
            $dir = $1;
        } else {
            $dir = './';
        }
        $ENV{MT_HOME} = $dir;
    }
    unshift @INC, File::Spec->catdir($dir, 'lib');
    unshift @INC, File::Spec->catdir($dir, 'extlib');
}

local $| = 1;
print "Content-Type: text/html\n\n";
print show_header();

my @CLASSES = qw( MT::Author MT::Blog MT::Category MT::Comment MT::Entry
                  MT::IPBanList MT::Log MT::Notification MT::Permission
                  MT::Placement MT::Template MT::TemplateMap MT::Trackback
                  MT::TBPing MT::Session MT::PluginData MT::Config );

use File::Spec;

my @DBSPECS = qw( DataSource ObjectDriver Database DBUser DBHost DBPassword );
my ($src_cfg, $dst_cfg);

eval {
    local $SIG{__WARN__} = sub { print "**** WARNING: $_[0]\n" };

    require MT;
    my $mt = MT->new() or die MT->errstr;

    my $cfg = $mt->{cfg};

    require CGI;
    my $q = CGI->new;
    foreach (@DBSPECS) {
        $src_cfg->{$_} = $q->param('src_' . $_) || '';
        $dst_cfg->{$_} = $q->param('dst_' . $_) || '';
    }

    # if src and dst dbspecs not given
    if (!$src_cfg->{ObjectDriver} ||
        ($src_cfg->{ObjectDriver} eq 'DBM' && !$src_cfg->{DataSource}) ||
        !$dst_cfg->{ObjectDriver} ||
        ($dst_cfg->{ObjectDriver} eq 'DBM' && !$dst_cfg->{DataSource})) {
        $src_cfg->{$_} ||= $cfg->$_() || '' foreach (@DBSPECS);
        print show_form($q->url || 'mt-db-convert.cgi', $src_cfg, $dst_cfg);
        print show_footer();
        exit;
    }

    require MT::Object;
    my $type = ($dst_cfg->{ObjectDriver} =~ /^DBI::(.*)$/) ? $1 : '';
    # set dst driver
    $cfg->set($_, $dst_cfg->{$_}) foreach (@DBSPECS);
    MT::Object->set_driver($dst_cfg->{ObjectDriver})
        or die MT::ObjectDriver->errstr;
    my $dbh = MT::Object->driver->{dbh};

    use MT::Upgrade;
    my @stmts;
    foreach (@CLASSES) {
        push @stmts, MT::Upgrade->check_class($_);
    }
    print "<pre>\n\n";
    print "Loading database schema...\n\n";
    MT::Upgrade->do_upgrade(Install => 1);

    ## %ids will hold the highest IDs of each class.
    my %ids;

    print "Loading data...\n";
    for my $class (@CLASSES, 'MT::FileInfo' ) {
        print $class, "\n";
        # set src driver
        $cfg->set($_, $src_cfg->{$_}) foreach (@DBSPECS);
        MT::Object->set_driver($src_cfg->{ObjectDriver});
        eval "use $class";
        my $iter = $class->load_iter;

        my %names;
        my %cat_parent;
        my $i = 0;

        # set dst driver
        $cfg->set($_, $dst_cfg->{$_}) foreach (@DBSPECS);
        MT::Object->set_driver($dst_cfg->{ObjectDriver});
        MT::Object->driver->{dbh}->begin_work if $type eq 'sqlite';
        while (my $obj = $iter->()) {
            # Update IDs only auto_increment.
            $ids{$class} = $obj->id
                if $obj->properties->{column_defs}->{id} =~ /auto_increment/ &&
                   (!$ids{$class} || $obj->id > $ids{$class});
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
            } elsif ($class eq 'MT::Comment') {
                $obj->visible(1) unless defined $obj->visible;
            } elsif ($class eq 'MT::TBPing') {
                $obj->visible(1) unless defined $obj->visible;
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

            $obj->save
                or die $obj->errstr;
            $i++;
            print '.' . (($i % 10) ? '' : ' ') . (($i % 100) ? '' : "\n");
        }

        # fix up the category parents
        foreach my $id (keys %cat_parent) {
            my $cat = MT::Category->load($id);
            $cat->parent( $cat_parent{$id} );
            $cat->save;
        }

        print "\n($i objects saved.)\n\n";
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

    $cfg->SchemaVersion(MT->schema_version(), 1);
    $cfg->save_config();
};
if ($@) {
    print <<HTML;

An error occurred while loading data:

$@

HTML
} else {
    print <<HTML;

Done copying data from $src_cfg->{ObjectDriver} to $dst_cfg->{ObjectDriver}! All went well.

HTML
}

print "</pre>\n";
print show_footer();

sub show_header {
    my $html = <<'HTML';
<html>
<head>
  <title>mt-db-convert.cgi: Converting your MT data between DB engines</title>
  <style type="text/css">
  body { font-family: "trebuchet ms", arial, sans-serif; font-size: 90%; }
    h1 { font-size: 100%; }
    fieldset { width: 40%; float: left; }
  </style>
</head>
<body>
<h1>mt-db-convert.cgi(Rev: $Rev$): Converting your MT data between DB engines</h1>
HTML
}

sub show_form {
    my ($name, $src_cfg, $dst_cfg) = @_;
    my (%src_sel, %dst_sel);
    for (qw( DBM DBI::mysql DBI::postgres DBI::sqlite )) {
        $src_sel{$_} = ($_ eq $src_cfg->{ObjectDriver}) ? 'selected' : '';
        $dst_sel{$_} = ($_ eq $src_cfg->{ObjectDriver}) ? 'selected' : '';
    }
    my $html = <<HTML;
<p>Please fill the following:</p>

<form method="post" action="$name">
  <fieldset>
    <legend>Source DB Configuration</legend>
    <dl>
      <dt>DataSource: (Required for BerkeleyDB)</dt>
      <dd><input name="src_DataSource" type="text" value="$src_cfg->{DataSource}" /></dd>
      <dt>ObjectDriver:</dt>
      <dd>
        <select name="src_ObjectDriver">
          <option value="">Select a driver</option>
          <option value="DBM" $src_sel{'DBM'}>BerkeleyDB</option>
          <option value="DBI::mysql" $src_sel{'DBI::mysql'}>MySQL</option>
          <option value="DBI::postgres" $src_sel{'DBI::postgres'}>PostgreSQL</option>
          <option value="DBI::sqlite" $src_sel{'DBI::sqlite'}>SQLite</option>
        </select>
      </dd>
      <dt>Database:</dt>
      <dd><input name="src_Database" type="text" value="$src_cfg->{Database}" /></dd>
      <dt>DBUser:</dt>
      <dd><input name="src_DBUser" type="text" value="$src_cfg->{DBUser}" /></dd>
      <dt>DBHost:</dt>
      <dd><input name="src_DBHost" type="text" value="$src_cfg->{DBHost}" /></dd>
      <dt>DBPassword:</dt>
      <dd><input name="src_DBPassword" type="password" value="" /></dd>
    </dl>
  </fieldset>

  <fieldset>
    <legend>Destination DB Configuration</legend>
    <dl>
      <dt>DataSource: (Required for BerkeleyDB)</dt>
      <dd><input name="dst_DataSource" type="text" value="$dst_cfg->{DataSource}" /></dd>
      <dt>ObjectDriver:</dt>
      <dd>
        <select name="dst_ObjectDriver">
          <option value="">Select a driver</option>
          <option value="DBM" $dst_sel{'DBM'}>BerkeleyDB</option>
          <option value="DBI::mysql" $dst_sel{'DBI::mysql'}>MySQL</option>
          <option value="DBI::postgres" $dst_sel{'DBI::postgres'}>PostgreSQL</option>
          <option value="DBI::sqlite" $dst_sel{'DBI::sqlite'}>SQLite</option>
        </select>
      </dd>
      <dt>Database:</dt>
      <dd><input name="dst_Database" type="text" value="$dst_cfg->{Database}" /></dd>
      <dt>DBUser:</dt>
      <dd><input name="dst_DBUser" type="text" value="$dst_cfg->{DBUser}" /></dd>
      <dt>DBHost:</dt>
      <dd><input name="dst_DBHost" type="text" value="$dst_cfg->{DBHost}" /></dd>
      <dt>DBPassword:</dt>
      <dd><input name="dst_DBPassword" type="password" value="$dst_cfg->{DBPassword}" /></dd>
    </dl>
  </fieldset>

  <p style="clear: both;"><input type="submit" value="Convert" /></p>
</form>
HTML
}

sub show_footer {
    my $html = <<'HTML';
<address>Hirotaka Ogawa (<a href="http://as-is.net/blog/">http://as-is.net/blog/</a>)</address>
</body>
</html>
HTML
}
