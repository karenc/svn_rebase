#!/bin/bash

# This is a script to generate README for github.com

export MANWIDTH=80
man -l svn_rebase.1 >README
echo -e "\n\n------------------------------------------------------------\n\n" >>README
man -l svn_merge.1 >>README
