#!/usr/bin/perl -w
# This code cannot be redistributed without permissions.
#
# mt-db-convert.cgi: converting your MT data between multiple data storage

use strict;
local $| = 1;

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

use CGI;

print "Content-Type: text/html\n\n";
print <<HTML;
<html>
<head><title>MT-DB-CONVERT: Converting your MT data</title></head>
<body>
<p><strong>MT-DB-CONVERT: Coverting your MT data</strong></p>

HTML

my @CLASSES = qw( MT::Author MT::Blog MT::Category MT::Comment MT::Entry
                  MT::IPBanList MT::Log MT::Notification MT::Permission
                  MT::Placement MT::Template MT::TemplateMap MT::Trackback
                  MT::TBPing );

my @DBSPECS = qw( DataSource ObjectDriver Database DBUser DBHost DBPassword );

require MT;
my $mt = MT->new(Config => $MT_DIR . 'mt.cfg', Directory => $MT_DIR)
  or die MT->errstr;
my $cfg = $mt->{cfg};

my $q = CGI->new;

my %src;
my %dest;

for my $dbspec (@DBSPECS) {
  $src{$dbspec} = $q->param('src_' . $dbspec) || '';
  $dest{$dbspec} = $q->param('dest_' . $dbspec) || '';
}

if (!$src{ObjectDriver} || ($src{ObjectDriver} eq 'DBM' && $src{DataSource}) ||
    !$dest{ObjectDriver} || ($dest{ObjectDriver} eq 'DBM' && $dest{DataSource})) {

  for my $dbspec (@DBSPECS) {
    $src{$dbspec} ||= $cfg->$dbspec();
  }

  my %src_selected = ('DBM' => '', 'DBI::mysql' => '', 'DBI::postgres' => '', 'DBI::sqlite' => '');
  my %dest_selected = ('DBM' => '', 'DBI::mysql' => '', 'DBI::postgres' => '', 'DBI::sqlite' => '');
  $src_selected{$src{ObjectDriver}} = 'selected' if $src{ObjectDriver};
  $dest_selected{$dest{ObjectDriver}} = 'selected' if $dest{ObjectDriver};
  print <<HTML;
<p>Please fill the following:</p>

<form method="post" action="$0">
<fieldset style="float:left; width:40%">
<legend>Source DB Configuration</legend>
<dl>
<dt>DataSource: (mandatory if using BerkeleyDB)</dt>
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
<dd><input name="src_DBPassword" type="password" value="$src{DBPassword}" /></dd>
</dl>
</fieldset>

<fieldset style="float:left; width:40%">
<legend>Destination DB Configuration</legend>
<dl>
<dt>DataSource: (mandatory if using BerkeleyDB)</dt>
<dd><input name="dest_DataSource" type="text" value="$dest{DataSource}" /></dd>
<dt>ObjectDriver:</dt>
<dd><select name="dest_ObjectDriver">
<option value="">Select a driver</option>
<option value="DBM" $dest_selected{'DBM'}>BerkeleyDB</option>
<option value="DBI::mysql" $dest_selected{'DBI::mysql'}>MySQL</option>
<option value="DBI::postgres" $dest_selected{'DBI::postgres'}>PostgreSQL</option>
<option value="DBI::sqlite" $dest_selected{'DBI::sqlite'}>SQLite</option>
</select></dd>
<dt>Database:</dt>
<dd><input name="dest_Database" type="text" value="$dest{Database}" /></dd>
<dt>DBUser:</dt>
<dd><input name="dest_DBUser" type="text" value="$dest{DBUser}" /></dd>
<dt>DBHost:</dt>
<dd><input name="dest_DBHost" type="text" value="$dest{DBHost}" /></dd>
<dt>DBPassword:</dt>
<dd><input name="dest_DBPassword" type="password" value="$dest{DBPassword}" /></dd>
</dl>
</fieldset>

<p style="clear:both;"><input type="submit" value="Convert" /></p>
</form>

HTML

} else {

  eval {
    local $SIG{__WARN__} = sub { print "**** WARNING: $_[0]\n" };

    require MT::Object;

    # Preload schema to the dest DB
    my ($type) = $dest{ObjectDriver} =~ /^DBI::(.*)$/;
    if ($type) {
      # set dest driver
      for my $dbspec (@DBSPECS) {
	$cfg->set($dbspec, $dest{$dbspec});
      }
      MT::Object->set_driver($dest{ObjectDriver})
	  or die MT::ObjectDriver->errstr;
      my $dbh = MT::Object->driver->{dbh};
      my $schema = File::Spec->catfile($MT_DIR, 'schemas', $type . '.dump');
      open FH, $schema or die "Can't open schema file '$schema': $!";
      my $ddl;
      { local $/; $ddl = <FH> }
      close FH;
      my @stmts = split /;/, $ddl;
      print "Loading database schema...\n\n";
      for my $stmt (@stmts) {
        $stmt =~ s!^\s*!!;
        $stmt =~ s!\s*$!!;
        next unless $stmt =~ /\S/;
        $dbh->do($stmt) or die $dbh->errstr;
      }
    }

    my %ids;

    for my $class (@CLASSES) {
      print "<p>Dumping $class:<br />\n";

      # set source driver
      for my $dbspec (@DBSPECS) {
	$cfg->set($dbspec, $src{$dbspec});
      }
      MT::Object->set_driver($src{ObjectDriver});

      eval "use $class";
      my $iter = $class->load_iter;

      my %names;

      # set dest driver
      for my $dbspec (@DBSPECS) {
	$cfg->set($dbspec, $dest{$dbspec});
      }
      MT::Object->set_driver($dest{ObjectDriver});

      my $i = 0;
      while (my $o = $iter->()) {
	$ids{$class} = $o->id
	  if !$ids{$class} || $o->id > $ids{$class};

	if ($class eq 'MT::Template') {
	  my $key = lc($o->name) . $o->blog_id;
	  if ($names{$class}{$key}++) {
	    print "        Found duplicate template name '" .
	      $o->name;
	    $o->name($o->name . ' ' . $names{$class}{$key});
	    print "'; renaming to '" . $o->name . "'\n";
	  }
	  ## Touch the text column to make sure we read in
	  ## any linked templates.
	  my $text = $o->text;
	} elsif ($class eq 'MT::Author') {
	  my $key = lc($o->name);
	  if ($names{$class . $o->type}{$key}++) {
	    print "        Found duplicate author name '" .
	      $o->name;
	    $o->name($o->name . ' ' . $names{$class}{$key});
	    print "'; renaming to '" . $o->name . "'\n";
	  }
	  $o->email('') unless defined $o->email;
	  $o->set_password('') unless defined $o->password;
	} elsif ($class eq 'MT::Category') {
	  my $key = lc($o->label) . $o->blog_id;
	  if ($names{$class}{$key}++) {
	    print "        Found duplicate category label '" .
	      $o->label;
	    $o->label($o->label . ' ' . $names{$class}{$key});
	    print "'; renaming to '" . $o->label . "'\n";
	  }
	} elsif ($class eq 'MT::Trackback') {
	  $o->entry_id(0) unless defined $o->entry_id;
	  $o->category_id(0) unless defined $o->category_id;
	} elsif ($class eq 'MT::Entry') {
	  $o->allow_pings(0)
	    if defined $o->allow_pings && $o->allow_pings eq '';
	  $o->allow_comments(0)
	    if defined $o->allow_comments && $o->allow_comments eq '';
	}


	$i++;
	print $o->save ? "." : "!<br />" . $o->errstr;
	$i % 10 or print " ";
	$i % 100 or print "<br />";
      }
      print "</p>\n\n";
    }
  };

  if ($@) {
    print <<HTML;
<p><strong>An error occurred while loading data: $@</strong></p>
</body>
</html>
HTML
  } else {
    print <<HTML;
<p><strong>Done copying data from $src{ObjectDriver} to $dest{ObjectDriver}.</strong></p>
</body>
</html>
HTML
  }
}
