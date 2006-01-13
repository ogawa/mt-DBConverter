#!/usr/bin/perl -w
# mt-tbfixer.cgi
# This script allows you to remove duplicated MT::Trackback objects,
# which can be often caused by mt-db2sql.cgi and previous versions of 
# mt-db-convert.cgi.  And it also maintains MT::TBPing objects to
# associate with the proper MT::Trackback object consistently.
#
# $Id$

use strict;
use lib 'lib';
use MT::Bootstrap;

package TBFixer;
use MT::App;
@TBFixer::ISA = qw( MT::App );
use MT::Trackback;
use MT::TBPing;

sub init {
    my $app = shift;
    $app->SUPER::init(@_) or return;
    $app->add_methods(check => \&fixer, fix => \&fixer);
    $app->{charset} = $app->{cfg}->PublishCharset;
    $app->{default_mode} = 'check';
    $app;
}

sub fixer {
    my $app = shift;
    my $mode = $app->mode;
    my $html = '<html><body><pre>';

    my $conflicted_tb = 0;
    my $conflicted_tbping = 0;
    my @trackbacks = MT::Trackback->load(undef, { sort => 'id', direction => 'descend' });
    my %tbs;
    for my $tb (@trackbacks) {
	my $eid = $tb->entry_id or next;
	unless (defined $tbs{$eid} && $tbs{$eid}->isa('MT::Trackback')) {
	    $tbs{$eid} = $tb;
	    next;
	}

	my $tb_id = $tbs{$eid}->id;
	$html .= "MT::Trackback(id=" . $tb->id . ") conflicts with (id=" . $tb_id . ") for entry " . $eid . "\n";
	$conflicted_tb++;

	my @pings = MT::TBPing->load({ tb_id => $tb->id });
	for my $ping (@pings) {
	    if ($mode eq 'fix') {
		$ping->tb_id($tb_id);
		$ping->save or die $ping->errstr;
	    }
	    $html .= "   MT::TBPing(id=" . $ping->id . ") " . ($mode eq 'fix' ? 'is' : 'can be') . " moved from MT::Trackback(id=" . $tb->id . ") to (id=" . $tb_id . ")\n";
	    $conflicted_tbping++;
	}

	$html .= "   MT::Trackback(id=" . $tb->id . ") " . ($mode eq 'fix' ? 'is' : 'can be') . " removed\n";

	if ($mode eq 'fix') {
	    $tb->remove or die $tb->errstr;
	}
    }
    $html .= "\n";
    if ($mode eq 'fix') {
	$html .= "$conflicted_tb conflicts are found and fixed in MT::Trackback!\n";
	$html .= "$conflicted_tbping conflicts are found and fixed in MT::TBPing!\n";
	$html .= "\nYou should perform rebuilding for all MT contents.\n"
	    if $conflicted_tb || $conflicted_tbping;
    } else {
	$html .= "$conflicted_tb conflicts are found in MT::Trackback!\n";
	$html .= "$conflicted_tbping conflicts are found in MT::TBPing!\n";
    }
    $html . '</pre></body></html>';
}

package main;
my $app = TBFixer->new;
$app->run;

1;
