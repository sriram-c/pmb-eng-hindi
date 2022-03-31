#!/usr/bin/env python
# -*- coding: utf8 -*-


'''
Read pmb-4.0.0 gold sbn files and correct the grouping of words according to Paninian notation
Take Hindi translation of the raw text of English and try to align it with English to create
the parallel meaning bank for Hindi.
'''

import argparse
import codecs
from collections import defaultdict
import re
import os
from os import path as op
import csv
import nltk




########################################

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Read English sbn file and correct the LWG(local word grouping) t and align with Hindi Translation')

    parser.add_argument(
        '--data', dest='data_dir', help='path of pmb data'
    )

    parser.add_argument(
        '--morph_data', dest='morph_data_dir', help='path for English and Hindi Lt-proc morph file'
    )

    parser.add_argument(
        '--translation_dir', dest='trans_dir',
        help='path for putting the extracted english sentence to be translated to Hindi'
    )

    parser.add_argument(
        '--eng_hnd_sen', dest='eng_hnd_sen',
        help='path for Hindi Translated file (For the English sentences obtained from sbn files'
    )

    parser.add_argument(
        '--eng_hnd_dict', dest='eng_hnd_dict',
        help='path for English Hindi Dictionary'
    )

    args = parser.parse_args()

    return args


def read_sbn_files(dir_path):
    """
    Reads the file 'en.drs.sbn' in the data dir recursively
    and return it as list of sbn and raw sentences
    """

    list_of_sbn = []
    list_of_eng_sen = []

    for i, (path, dirs, files) in enumerate(os.walk(dir_path), start=1):
        if dirs: continue  # document directories have no directories inside
        sbn_file = op.join(path, 'en.drs.sbn')
        eng_file = op.join(path, 'en.raw')
        list_of_sbn.append(read_sbn(sbn_file))
        list_of_eng_sen.append(read_eng_sen(eng_file))

    return [list_of_sbn, list_of_eng_sen]


def read_sbn(file_path):
    """reads the sbn_file and return it as a list"""
    sbn = []
    with open(file_path) as f:
        for line in f:
            if line.startswith('%'): continue
            sbn.append(line.strip())
    return sbn


def read_eng_sen(file_path):
    """reads eng sen from 'en.raw' file"""
    with open(file_path) as f:
        return f.read().strip()

def write_file(dir_path, file_name, cont):
    """Write content of list to file"""

    if not op.exists(dir_path): os.makedirs(dir_path)
    with open(op.join(dir_path, file_name), 'w') as f:
        for l in cont:
            f.write('{}\n'.format(l))


def is_content(word):
    if re.match(r'.*\.[avnr]\.\d\d$', word): return True

def is_verb(word): # for matching only verb
    if re.match(r'.*\.[v]\.\d\d$', word): return True

def get_word_info(sbn_word):
    """Get the lexical, role and surface word info from sbn info"""

    m =  re.match(r'([^\s]*)\s+([^%]+)%\s+([^[]+)\s+(.*)', sbn_word)
    if m:
        lex = m.group(1)
        role = m.group(2)
        wd = m.group(3)
        pos_count = m.group(4)

    return lex, role, wd, pos_count

def get_vb_chunks(sen):
    """ Get chunks for the English sentences using spacy"""
    words = nltk.word_tokenize(sen)
    tagged = nltk.pos_tag(words)

    vb_chunks = []
    grammar = "VP: {<ADV>*<VB.*>+}"
    cp = nltk.RegexpParser(grammar)
    result = cp.parse(tagged)
    for t in result.subtrees():
        if(t.label() == 'VP'): vb_chunks.append(list(zip(*t.leaves()))[0])
    return  vb_chunks


def get_lwg(verb, eng_hnd_sen):
    """ Get the correct lwg(local word grouping) of the verb in the sentence"""

    root, wn_sense = re.split(r'\.', verb, 1)
    eng, hnd = eng_hnd_sen
    vb_chunks = get_vb_chunks(eng)
    lwg = ''
    for chunk in vb_chunks:
        for wd in chunk:
            if root in wd: lwg = chunk

    return  lwg


def get_hindi_wd(eng_wd, lwg, eng_hnd_sen):
    """ Get the HIndi equivalent word for English_wd"""

    root, wn_sense = re.split(r'\.', eng_wd, 1)
    eng_sen, hnd_sen = eng_hnd_sen

    print('yes')


def dic_process(E_H_dic):
    # read English-Hindi dictionary
    # store it in dictionary without the category info
    E_H_dic_processed = {}
    for line in E_H_dic:
        a =   (re.match('^#', line))
        if not(a):
            eng_wd_catg = line.split('\t')[0]
            eng_wd = eng_wd_catg.split('_')[0]
            hnd_wd = line.split('\t')[1].strip()
            hnd_wd_list = []
            if '/' in hnd_wd:
                hnd_wd_list = hnd_wd.split('/')
            else:
                hnd_wd_list.append(hnd_wd)

            if eng_wd in E_H_dic_processed:
                E_H_dic_processed[eng_wd].extend(hnd_wd_list)
            else:
                E_H_dic_processed[eng_wd] = hnd_wd_list

    return  E_H_dic_processed

def read_eng_hnd_dic(file_path):
    #Read English Hindi dictionary and return as dict

    eng_hnd_dict = defaultdict(dict)
    with open(file_path, 'r')as f:
        for line in f.readlines():
            if not (re.match(r'^#', line)):
                eng, hnd = line.strip().split('\t')
                try:
                    if re.search(r'_', eng): wd, catg = eng.split('_', 1)
                    else: wd = eng
                except ValueError:
                    print("WARNING: Skipping word {} in English Hindi dictionary".format(eng))
                hnd_wd_list = hnd.split('/')
                if wd in eng_hnd_dict:
                    for l in hnd_wd_list: eng_hnd_dict[wd].append(l)
                else: eng_hnd_dict[wd] = hnd_wd_list
    f.close()

    return  eng_hnd_dict




def sen_align(sbn_sen_info, eng_hnd_sen):
    """
    Correct the LWG(Local word grouping) of the Eng_sen and rewrite the sbn
    For each sentence align the sbn info with Hindi words
    """

    sbn_eng_hnd = []
    for sbn_word in sbn_sen_info:
        lex, rol, wd, pos_count = get_word_info(sbn_word)
        correct_lwg = get_lwg(lex, eng_hnd_sen) if is_verb(lex) else '' # If verb find correct LWG
        hnd_wrd = get_hindi_wd(lex, correct_lwg, eng_hnd_sen) if is_content(lex) else ''
        sbn_eng_hnd.append((lex, rol, wd, pos_count, correct_lwg, hnd_wrd))

    return  sbn_eng_hnd


def sbn_align(sbn_file, eng_hnd_data):
    """
    Re-write sbn file using correct grouping in English according to Paninian grammar
    and aligns the Hindi translation side by side
    """
    #read each sen in sbn_file and align with Hindi sen
    #priority on content words
    sbn_align = []
    for sbn_sen_info, eng_hnd_sen in zip(sbn_file, eng_hnd_data):
        sbn_eng_hnd = sen_align(sbn_sen_info, eng_hnd_sen)
        sbn_align.append(sbn_eng_hnd)

    return  sbn_align


if __name__ == '__main__':
    args = parse_arguments()

    # read sbn and raw english sentences from pmb data dir
    [sbn, eng_sen] = read_sbn_files(args.data_dir)
    assert len(eng_sen) == len(sbn), \
        'sbn no {} and English sen {} do not match'.format(len(sbn), len(eng_sen))

    # Write Eng_sen to file for translating it through NMT or Manual
    write_file(args.trans_dir, 'eng_raw_sen.txt', eng_sen)

    print('Using already translated Hindi sen file(by Google NMT)')
    with codecs.open(args.eng_hnd_sen, 'r', encoding='UTF-8') as f:
        eng_hnd_data = list(csv.reader(f))

    ####### ALIGNING with HIndi ############
    e_h_dict = read_eng_hnd_dic(args.eng_hnd_dict)
    sbn_aligned = sbn_align(sbn, eng_hnd_data) #rewrite sbn file
    print('Done')
