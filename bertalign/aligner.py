import numpy as np

from bertalign import model as default_model
from bertalign.encoder import Encoder
from bertalign.corelib import *
from bertalign.utils import *


class Bertalign:
    def __init__(self,
                 src,
                 tgt,
                 max_align=5,
                 top_k=3,
                 win=5,
                 skip=-0.1,
                 margin=True,
                 len_penalty=True,
                 is_split=False,
                 src_lang=None,
                 tgt_lang=None,
                 model=None,
                 fix_side=None
                 ):

        self.max_align = max_align
        self.top_k = top_k
        self.win = win
        self.skip = skip
        self.margin = margin
        self.len_penalty = len_penalty
        if model != None:
            self.model = Encoder(model)

        else:
            self.model = default_model

        src = clean_text(src)
        tgt = clean_text(tgt)
        src_lang = (src_lang in LANG.SPLITTER and src_lang) or detect_lang(src)
        tgt_lang = (tgt_lang in LANG.SPLITTER and tgt_lang) or detect_lang(tgt)

        if is_split:
            src_sents = src.splitlines()
            tgt_sents = tgt.splitlines()
        else:
            src_sents = split_sents(src, src_lang)
            tgt_sents = split_sents(tgt, tgt_lang)

        src_num = len(src_sents)
        tgt_num = len(tgt_sents)

        print("Source language: {}, Number of sentences: {}".format(src_lang, src_num))
        print("Target language: {}, Number of sentences: {}".format(tgt_lang, tgt_num))

        print("Embedding source and target text using {} ...".format(
            self.model.model_name))
        src_vecs, src_lens = self.model.transform(src_sents, max_align - 1)
        tgt_vecs, tgt_lens = self.model.transform(tgt_sents, max_align - 1)

        char_ratio = np.sum(src_lens[0,]) / np.sum(tgt_lens[0,])

        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.src_sents = src_sents
        self.tgt_sents = tgt_sents
        self.src_num = src_num
        self.tgt_num = tgt_num
        self.src_lens = src_lens
        self.tgt_lens = tgt_lens
        self.char_ratio = char_ratio
        self.src_vecs = src_vecs
        self.tgt_vecs = tgt_vecs
        self.fix_side = fix_side

    def align_sents(self):

        print("Performing first-step alignment ...")
        D, I = find_top_k_sents(
            self.src_vecs[0, :], self.tgt_vecs[0, :], k=self.top_k)
        first_alignment_types = get_alignment_types(2)  # 0-1, 1-0, 1-1
        first_w, first_path = find_first_search_path(
            self.src_num, self.tgt_num)
        first_pointers = first_pass_align(
            self.src_num, self.tgt_num, first_w, first_path, first_alignment_types, D, I)
        first_alignment = first_back_track(
            self.src_num, self.tgt_num, first_pointers, first_path, first_alignment_types)

        print("Performing second-step alignment ...")
        second_alignment_types = get_alignment_types(self.max_align)
        if self.fix_side:
            assert self.fix_side == 'src' or 'tgt', 'Please choose between src, tgt or None!'
            # If src/tgt selected, bertalign will NOT modify chosen side during alignment process
            # Removes 2-1, 3-1,... or 1-2, 1-3,... respectively
            if self.fix_side == 'src':
                updated_types = [
                    a_type for a_type in second_alignment_types if a_type[0] == 0 or a_type[0] == 1]
            else:
                updated_types = [
                    a_type for a_type in second_alignment_types if a_type[1] == 0 or a_type[1] == 1]
            second_alignment_types = np.array(updated_types)

        second_w, second_path = find_second_search_path(
            first_alignment, self.win, self.src_num, self.tgt_num)
        second_pointers = second_pass_align(self.src_vecs, self.tgt_vecs, self.src_lens, self.tgt_lens,
                                            second_w, second_path, second_alignment_types,
                                            self.char_ratio, self.skip, margin=self.margin, len_penalty=self.len_penalty)
        second_alignment = second_back_track(
            self.src_num, self.tgt_num, second_pointers, second_path, second_alignment_types)

        print("Finished! Successfully aligned {} {} sentences to {} {} sentences ({})\n".format(
            self.src_num, self.src_lang, self.tgt_num, self.tgt_lang, len(second_alignment)))
        self.result = second_alignment

    def get_sents(self):
        src_sents = []
        tgt_sents = []
        for bead in (self.result):
            src_sents.append(self._get_line(bead[0], self.src_sents))
            tgt_sents.append(self._get_line(bead[1], self.tgt_sents))
        return src_sents, tgt_sents

    def print_sents(self, file=None):
        for bead in (self.result):
            src_line = self._get_line(bead[0], self.src_sents)
            tgt_line = self._get_line(bead[1], self.tgt_sents)
            print(src_line + "\n" + tgt_line + "\n", file=file)

    @staticmethod
    def _get_line(bead, lines):
        line = ''
        if len(bead) > 0:
            line = ' '.join(lines[bead[0]:bead[-1]+1])
        return line
