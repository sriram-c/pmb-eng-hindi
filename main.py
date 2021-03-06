#!/usr/bin/env python
# -*- coding: utf8 -*-


'''
Read pmb-4.0.0 gold sbn files and correct the grouping of words according to Paninian notation
Take Hindi translation of the raw text of English and try to align it with English to create
the parallel meaning bank for Hindi.


to do
done 1. show output in utf8 (integrate wx-utf8 converter)
2. resolve unix/windows dir reading sequence mismatch
3. use English wd to search hindi dic (currently taking left side word only)
4. use trnasliteration logic (or fuzzy match) to align NER (names)
5. in LWG (Verb) show root + tam

'''

import argparse
import codecs
from collections import defaultdict
import re
import os
from os import path as op
import csv
import nltk
from wxconv import WXC
from fuzzywuzzy import fuzz

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

from ai4bharat.transliteration import XlitEngine
con = WXC(order='wx2utf', lang='hin')

tranl_e = XlitEngine("hi")
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

    parser.add_argument(
        '--hnd_tam_dict', dest='hnd_tam_dict',
        help='path for Hindi Tam all form dictionary'
    )

    parser.add_argument(
        '--hnd_morph_dict', dest='hnd_morph_dict',
        help='path for Hindi morph dict prepared for the Hindi translated files'
    )

    parser.add_argument(
        '--controlled_dict', dest='cdict',
        help='path for English Hindi Controlled Dictionary (user given meanings if not in large English Hindi dictionary)'
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
            sbn.append(line.rstrip('\n'))
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

    lex, role, surf_wd, pos_count = '', '', '', ''

    try:
        m =  re.match(r'([^\s]*)\s+([^%]+)%\s+([^[]+)\s+(.*)', sbn_word)
        if m:
            lex = m.group(1)
            role = m.group(2)
            surf_wd = m.group(3)
            pos_count = m.group(4)
    except:
        print("ERROR: Skipping pattern {} in the sbn file".format(sbn_word))

    return lex, role, surf_wd, pos_count

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

                hnd_wd_list = []
                for l in hnd.split('/'):
                    if len(l.split('_')) <= 2:
                        if len(l.split('_')) == 2:
                                if re.match(r'.*kara|.*ho|.*nA', l): hnd_wd_list.append(l.split('_')[0])
                                else: hnd_wd_list.append(re.sub('_', ' ', l))
                        else: hnd_wd_list.append(l)

                if wd in eng_hnd_dict:
                    for l in hnd_wd_list: eng_hnd_dict[wd].append(l)
                else: eng_hnd_dict[wd] = hnd_wd_list

    return  eng_hnd_dict

def read_eng_hnd_cdic(file_path):
    e_h_cdict = defaultdict(dict)
    with open(file_path) as f:
        for line in f.readlines():
            try:
                eng, hnd = line.strip().split('\t')
                e_h_cdict[eng] = hnd
            except: print("ERROR: Skipping in reading controlled dictionary for pattern {}".format(line))

    return  e_h_cdict



def read_hnd_tam_dic(file_path):
    """ Read the HIndi tam all form dictionary and create a dictionary on the 2nd col"""

    hnd_tam_dict = defaultdict(dict)
    with open(file_path,'r') as f:
        for line in f.readlines():
            try:
                info, tam = re.split(r'\s\s*', line.strip())
            except:
                print("ERROR: Skipping in tam dictionary please check pattern {}".format(line))

            tam_wd = tam.split('_', 1)[1] if re.match(r'^0', tam) else tam
            hnd_tam_dict[tam_wd] = 1

    return hnd_tam_dict

def read_hnd_morph_dic(file_path):
    """Read HIndi morph generated by lt-proc command for the Hindi Translated file
    todo_morph: use system cmd to run lt-proc dynamically on Hindi translated file"""

    hnd_morph_dict = defaultdict(dict)
    with open(file_path, 'r') as f:
        for line in f.readlines():
            try:
                wd, morph = line.strip().split('\t')
                root = list(set([l.split('<')[0]  for l in morph.split('/') if re.search(r'<', l)]))
                hnd_morph_dict[wd] = root
            except: print('ERROR in pattern in morph dictionary {}'.format(line))

    return hnd_morph_dict



def get_hnd_vb_lwg(eng_root, surf_wd, eng_vb_lwg, hnd_sen, e_h_dict, hnd_tam_dict, hnd_morph_dict, hnd_sen_root, e_h_cdict):
    """ Get the HIndi equivalent VB LWG from the Hindi Sentence
    by using Hindi TAM Dictionary"""

    hnd_vb_lwg = []
    hnd_vb_root =  search_hnd_dict(eng_root, surf_wd, hnd_sen, e_h_dict, hnd_sen_root, e_h_cdict)

    if hnd_vb_root != '' :
        #match the vb lwg with a window size 4 in the right
        pos = hnd_sen.split().index(hnd_vb_root) + 1
        for i in range(pos+4, pos, -1):
            if(len(hnd_sen.split()) > i-1):
                tam = '_'.join(hnd_sen.split()[pos:i])
                if tam in hnd_tam_dict:
                    hnd_vb_lwg = hnd_vb_root+'+'+'0_'+' '.join(tam.split('_'))
                    return hnd_vb_lwg

    return hnd_vb_root



def search_hnd_dict(eng_wd, surf_wd, hnd_sen, e_h_dict, hnd_sen_root, e_h_cdict):

    """ Get the List of Hindi words  form HIndi dictionary ( and controlled dict ) for the English word and search
    it in the Hindi sentence  (both surface form and root form)  to get the exact usage."""

    hnd_dic_list = []

    hnd_wd = ''


    if not re.match(r'entity|time|person', eng_wd) and eng_wd != '':
        wd = eng_wd.lower()
        if wd in e_h_dict: # for regular dict
            hnd_dic_list.extend(e_h_dict[wd])
        if wd in e_h_cdict: #for controlled dict
            hnd_dic_list.append(e_h_cdict[wd])

    surf_wd_new = []
    for wd in surf_wd.strip().split():
        wd1 = re.sub(r'\.|\?', '', wd)
        if not re.match(r'^(in|on|for|to|from|up|a|an|the)$', wd1.lower()): surf_wd_new.append(wd1)

    for wd in surf_wd_new: # for surface words
        if wd != eng_wd and  wd.lower() in e_h_dict: hnd_dic_list.extend(e_h_dict[wd.lower()])

    hnd_wd =search_dic(hnd_sen, hnd_sen_root, list(set(hnd_dic_list)))

    if(hnd_wd != ''): return hnd_wd

    #Do Transliterate and search
    if not re.match(r'entity|time|person|company', eng_wd): surf_wd_new.append(eng_wd)

    if len(surf_wd_new) > 0: return search_transliterate_dic(list(set(surf_wd_new)), hnd_sen, hnd_sen_root)

    return ''



def search_transliterate_dic(eng_wds, hnd_sen, hnd_sen_root):
    #if Hindi meaning not found match with transliteration of English word (e.g keyboard -> kIbord)

    hnd_wd = []
    for wd in eng_wds:
        if wd:
            twd_dict = []
            out = tranl_e.translit_word(wd, topk=5, beam_width=10)
            for twd in out['hi']:
                twd_dict.append(transliterate(twd, sanscript.DEVANAGARI, sanscript.WX))

            if search_dic(hnd_sen, hnd_sen_root, twd_dict):
                hnd_wd.append(search_dic(hnd_sen, hnd_sen_root, twd_dict))

    return  ' '.join(hnd_wd)

def search_dic(hnd_sen, hnd_sen_root, hnd_dic_list):

    #for matching sub set of words e.g 'mAnava nirmiwa'
    for wd in hnd_dic_list:
        if re.match(r'.*-.*', wd):
            wd1 = re.sub(r'-|_', ' ', wd)
            if wd1 in hnd_sen: return  wd1
    for wd in hnd_sen.split():
        if wd in hnd_dic_list:
            return wd
    for root in hnd_sen_root:
        if root in hnd_dic_list:
            return hnd_sen_root[root]
    for wd in hnd_sen.split():
        for wd1 in hnd_dic_list:
            if fuzz.ratio(wd, wd1) > 77: return wd
    for wd in hnd_sen_root:
        for wd1 in hnd_dic_list:
            if fuzz.ratio(wd, wd1) > 77: return hnd_sen_root[wd]

    return ''


def get_hindi_wd(eng_wd, surf_wd, eng_vb_lwg, eng_hnd_sen, e_h_dict, hnd_tam_dict, hnd_morph_dict, hnd_sen_root, e_h_cdict):
    """ Get the HIndi equivalent word for English_wd"""

    eng_root, wn_sense = re.split(r'\.', eng_wd, 1) if eng_wd else ['', '']
    eng_sen, hnd_sen = eng_hnd_sen

    if eng_vb_lwg != '':
        hnd_wrd = get_hnd_vb_lwg(eng_root, surf_wd, eng_vb_lwg, hnd_sen, e_h_dict, hnd_tam_dict, hnd_morph_dict, hnd_sen_root, e_h_cdict)
    else:
        hnd_wrd = search_hnd_dict(eng_root, surf_wd, hnd_sen, e_h_dict, hnd_sen_root, e_h_cdict)

    return  hnd_wrd




def get_hnd_wd_with_bvkt(hnd_sen):
    hnd_wd_with_bvkt = {}
    hnd_wd = hnd_sen.split()
    for i in range(0, len(hnd_sen.split())):
        wd = hnd_sen.split()[i]
        prev_wd = hnd_sen.split()[i-1]
        if re.match(r'^(meM|se|ne|ko|ke|para|vAlA)$', wd):
            hnd_wd_with_bvkt[prev_wd] = prev_wd+'_'+wd

    return hnd_wd_with_bvkt



def sbn_sen_align(*argv):
    """
    Correct the LWG(Local word grouping) of the Eng_sen and rewrite the sbn
    For each sentence align the sbn info with Hindi words
    """
    sbn_sen_info = argv[0]
    eng_hnd_sen = argv[1]
    e_h_dict = argv[2]
    hnd_tam_dict = argv[3]
    hnd_morph_dict = argv[4]
    e_h_cdict = argv[5]

    eng_sen, hnd_sen = eng_hnd_sen
    hnd_sen_root = defaultdict(dict)
    for wd in hnd_sen.split():
        for hnd_root in hnd_morph_dict[wd]:
            hnd_sen_root[hnd_root] = wd

    hnd_wd_with_bvkt = get_hnd_wd_with_bvkt(hnd_sen)
    sbn_eng_hnd_sen = []
    for sbn_word in sbn_sen_info:
        lex, rol, surf_wd, pos_count = get_word_info(sbn_word)

        '''
        if(re.match(r'.*time.*', sbn_word)):
            print('yes')
        '''
        correct_lwg = get_lwg(lex, eng_hnd_sen) if is_verb(lex) else '' # If verb find correct LWG
        hnd_wrd = get_hindi_wd(lex, surf_wd, correct_lwg, eng_hnd_sen, e_h_dict, hnd_tam_dict, hnd_morph_dict, hnd_sen_root, e_h_cdict)

        if hnd_wrd in hnd_wd_with_bvkt:
            hnd_wrd = hnd_wd_with_bvkt[hnd_wrd]

        correct_lwg = '_'.join(correct_lwg)
        hnd_wrd_utf8 = con.convert(hnd_wrd) if hnd_wrd else ''

        sbn_eng_hnd_sen.append((lex, rol,'%%English', surf_wd, pos_count, correct_lwg, '%%Hindi', hnd_wrd_utf8))

    return  sbn_eng_hnd_sen


#def sbn_align_all(sbn_file, eng_hnd_data, e_h_dict, hnd_tam_dict):
def sbn_align_all(*argv):

    """
    Re-write sbn file using correct grouping in English according to Paninian grammar
    and aligns the Hindi translation side by side
    """
    sbn_file = argv[0]
    eng_hnd_data = argv[1]
    e_h_dict = argv[2]
    hnd_tam_dict = argv[3]
    hnd_morph_dict = argv[4]
    e_h_cdict = argv[5]
    sbn_align_all = []

    counter = 1
    for sbn_sen_info, eng_hnd_sen in zip(sbn_file, eng_hnd_data):
        try:
            sbn_eng_hnd = sbn_sen_align(sbn_sen_info, eng_hnd_sen, e_h_dict, hnd_tam_dict, hnd_morph_dict, e_h_cdict)
            sbn_align_all.append(sbn_eng_hnd)
            counter += 1
            if(counter > 100): return  sbn_align_all
        except:
            print("ERROR in sentence {}".format(eng_hnd_sen))
            counter += 1

    return  sbn_align_all


if __name__ == '__main__':
    args = parse_arguments()


    ####### READ ALL SBN FILES ###########

    # read sbn and raw english sentences from pmb data dir
    [sbn, eng_sen] = read_sbn_files(args.data_dir)
    assert len(eng_sen) == len(sbn), \
        'sbn no {} and English sen {} do not match'.format(len(sbn), len(eng_sen))

    # Write Eng_sen to file for translating it through NMT or Manual
    write_file(args.trans_dir, 'eng_raw_sen.txt', eng_sen)

    ####### ALIGNING with HIndi ############

    print('Using already translated Hindi sen file(by Google NMT)')
    with codecs.open(args.eng_hnd_sen, 'r', encoding='ISO-8859-1') as f:
        eng_hnd_data = list(csv.reader(f))

    e_h_dict = read_eng_hnd_dic(args.eng_hnd_dict)
    e_h_cdict = read_eng_hnd_cdic(args.cdict)
    hnd_tam_dict = read_hnd_tam_dic(args.hnd_tam_dict)
    hnd_morph_dict = read_hnd_morph_dic(args.hnd_morph_dict)

    sbn_aligned = sbn_align_all(sbn, eng_hnd_data, e_h_dict, hnd_tam_dict, hnd_morph_dict, e_h_cdict) #rewrite sbn file

    with open('output.txt', 'w', encoding='utf-8') as f:
        for sen, sbn in zip(eng_hnd_data, sbn_aligned):
            eng, hnd = sen
            hnd_utf8 = con.convert(hnd)
            f.write("{}\n{}\n".format(str(eng), str(hnd_utf8)))
            for s in sbn:
                try:
                    f.write("\n{}\n".format('\t'.join(s)))
                except:
                    print('ERROR in writing to file {}'.format(s))
            f.write('\n#########################\n')
    f.close()

