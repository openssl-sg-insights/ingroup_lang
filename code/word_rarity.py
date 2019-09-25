# get word counts in each subreddit 
import os
from pyspark import SparkConf, SparkContext
from pyspark.sql import SQLContext
import json
from collections import Counter
import operator
import re, string
import csv

#ROOT = '/global/scratch/lucy3_li/ingroup_lang/'
ROOT = '/data0/lucy/ingroup_lang/'
WORD_COUNT_DIR = ROOT + 'logs/word_counts/'
PMI_DIR = ROOT + 'logs/pmi/'
SR_DATA_DIR = ROOT + 'subreddits2/'
LOG_DIR = ROOT + 'logs/'

conf = SparkConf()
sc = SparkContext(conf=conf)
sqlContext = SQLContext(sc)

regex = re.compile('[%s]' % re.escape(string.punctuation))

def count_words(): 
    """
    Get word counts in each subreddit
    
    Currently askreddit is broken
    """
    log_file = open(LOG_DIR + 'counting_log.temp', 'w')
    for filename in os.listdir(SR_DATA_DIR):  
	if filename == 'askreddit': continue
	log_file.write(filename + '\n') 
	path = SR_DATA_DIR + filename 
	log_file.write('\tReading in textfile\n')
	data = sc.textFile(path)
	data = data.flatMap(lambda line: line.split(' '))
	data = data.map(lambda word: (word, 1))
	log_file.write('\tReducing by key...\n') 
	data = data.reduceByKey(lambda a, b: a + b)
	df = sqlContext.createDataFrame(data, ['word', 'count'])
	outpath = WORD_COUNT_DIR + filename
	df.write.mode('overwrite').parquet(outpath) 
    log_file.close() 

def calculate_pmi(percent_param=0.2): 
    """
    PMI is defined as 
    log(p(word|community) / p(word)) 
    or 
    log(frequency of word in community c / frequency of word in 
    all c's we are looking at)
    as defined in Zhang et al. 2017.
    
    @output: 
        - dictionaries for each doc of word : pmi 
        - docs: list of docs in order of matrix
        - words: list of words in order of matrix
    """
    log_file = open(LOG_DIR + 'pmi.temp', 'w')
    with open(LOG_DIR + 'total_word_counts.json', 'r') as infile: 
        total_counts = json.load(infile)
    docs = sorted(os.listdir(WORD_COUNT_DIR))
    for filename in sorted(os.listdir(WORD_COUNT_DIR)): 
        pmi_d = {}
        if os.path.isdir(WORD_COUNT_DIR + filename): 
            log_file.write(filename + '\n') 
            parquetFile = sqlContext.read.parquet(WORD_COUNT_DIR + filename + '/')
            d = Counter(parquetFile.toPandas().set_index('word').to_dict()['count'])
            num_top_p = int(percent_param*len(d))
            for w in d.most_common(num_top_p): 
                pmi_d[w[0]] = d[w[0]] / float(total_counts[w[0]])
            new_filename = filename.replace('.txt', '')
            with open(PMI_DIR + new_filename + '_' + str(percent_param) + '.csv', 'w') as outfile: 
                sorted_d = sorted(pmi_d.items(), key=operator.itemgetter(1))
                writer = csv.writer(outfile)
                writer.writerow(['word', 'pmi', 'count'])
                for tup in sorted_d: 
                    writer.writerow([tup[0].encode('utf-8', 'replace'), str(tup[1]), str(d[tup[0]])])
    log_file.write("DONE\n")
    log_file.close()
    
def count_overall_words(percent_param=0.2): 
    vocab = set()
    log_file = open(LOG_DIR + 'counting_all_log.temp', 'w') 
    log_file.write("Getting vocab...\n")
    for filename in sorted(os.listdir(WORD_COUNT_DIR)): 
        if os.path.isdir(WORD_COUNT_DIR + filename): 
            log_file.write(filename + '\n') 
            parquetFile = sqlContext.read.parquet(WORD_COUNT_DIR + filename + '/')
            d = Counter(parquetFile.toPandas().set_index('word').to_dict()['count'])
            num_top_p = int(percent_param*len(d))
            for w in d.most_common(num_top_p): 
                vocab.add(w[0])
    log_file.write("Vocab size:" + str(len(vocab)) + "\n")
    rdd1 = sc.emptyRDD()
    all_counts = Counter()
    for filename in sorted(os.listdir(WORD_COUNT_DIR)): 
        if os.path.isdir(WORD_COUNT_DIR + filename): 
            log_file.write(filename + '\n') 
            parquetFile = sqlContext.read.parquet(WORD_COUNT_DIR + filename + '/')
            rdd2 = parquetFile.rdd.map(tuple)
            # filter to only words in our vocab
            rdd2 = rdd2.filter(lambda tup: tup[0] in vocab)
            rdd1 = rdd2.union(rdd1).reduceByKey(lambda x,y : x+y)
            d = Counter(parquetFile.toPandas().set_index('word').to_dict()['count'])
            all_counts += d
    with open(LOG_DIR + 'total_word_counts.json', 'w') as outfile: 
        json.dump(all_counts, outfile)
    log_file.write("DONE\n")
    #df = sqlContext.createDataFrame(rdd1, ['word', 'count'])
    #df.write.mode('overwrite').parquet(LOG_DIR + 'total_word_counts') 
    log_file.close()

def word_tfidf(): 
    """
    tf-idf is defined as 
    (1 + log tf)xlog_10(N/df) where N is the 
    number of documents, or subreddits. tf is
    term frequency in document and df is
    number of documents the term appears in.

    @output: 
        - matrix of doc x word tf-idf'
        - docs: list of docs in order of matrix
        - words: list of words in order of matrix
    """
    pass

def niche_disem():
    """
    Altmann's metric, but for subreddits instead of users
    """
    pass

def main(): 
    #count_words()
    count_overall_words()
    calculate_pmi()
    sc.stop()

if __name__ == '__main__':
    main()
