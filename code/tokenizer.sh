#!/bin/bash
# Tokenizes each subreddit's file and removes duplicates

file_list=/data0/lucy/ingroup_lang/logs/file_list.txt
echo -n > $file_list
for filename in /data0/lucy/ingroup_lang/subreddits_month/*; do
    justfile=$(basename $filename)
    output_folder=/data0/lucy/ingroup_lang/subreddits3/$justfile
    mkdir -p $output_folder
    echo "/data0/lucy/ingroup_lang/subreddits_month/$justfile/RC_sample" >> $file_list
done
cat $file_list | parallel --jobs 10 'python tokenizer_helper.py {}' &
wait
