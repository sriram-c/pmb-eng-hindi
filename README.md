# Alignment of PMB(parallel meaning bank) with Hindi

A tool to automatically align English PMB annotations with equivalent Hindi Translated sentences.
## Install

    pip install -r requirements.txt

## Run

    python3 main.py --data data --eng_hnd_dict resources/eng_hnd_dic.txt --eng_hnd_sen translations/english_hindi_sen-wx.csv --translation_dir translations --hnd_tam_dict resources/hnd_tam_all_form --hnd_morph_dict translations/hnd-morph-dict.txt --controlled_dict resources/controlled_dictionary.txt

## Output

Output will be generated in 'output.txt' file. A sample generated output ('output.txt') is given.
