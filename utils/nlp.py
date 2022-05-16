import yaml
import numpy as np
from kanjize import kanji2int


def analyze_comments(
    comments: list, pos: str = '名詞', tokenizer: str = 'janome'
):
    if tokenizer == 'janome':
        from janome.tokenizer import Tokenizer
        tokenizer = Tokenizer()

        def tokenize(comment):
            result = [
                token.base_form
                for token in tokenizer.tokenize(comment)
                if token.part_of_speech.split(',')[0] in [pos]
                and token.base_form not in exclude_noun
                and not all([(s in n_chrs) for s in token.base_form])
            ]
            return [w for w in result if w]

    elif tokenizer == 'sudachi':
        from sudachipy import dictionary, tokenizer
        try:
            tokenizer_obj = dictionary.Dictionary().create()
        except:
            tokenizer_obj = dictionary.Dictionary(dict_type='small').create()

        def tokenize(comment):
            result = [
                token.dictionary_form()
                for token in tokenizer_obj.tokenize(
                    comment, mode=tokenizer.Tokenizer.SplitMode.C
                )
                if token.part_of_speech()[0] in [pos]
                and token.surface() not in exclude_noun
                and not all([(s in n_chrs) for s in token.surface()])
            ]
            return [w for w in result if w]

    # 絵文字や記号など必要ないものは(力技で)まとめて除去
    symbol_s, symbol_e = 44, 57
    Alphabet_s, Alphabet_e = 65, 90
    alphabet_s, alphabet_e = 97, 122
    Hiragana_s, Hiragana_e = 12353, 12438
    Katakana_s, Katakana_e = 12449, 12534
    katakana_s, katakana_e = 65382, 65439
    Kanji_s, Kanji_e = 19968, 40959
    exceptions = [
        32,  # ' '
        37,  # '%'
        12289,  # '、'
        12290,  # '。'
        12540   # 'ー'
    ]

    zen2han = {chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}
    etc_sym = {'〜': 'ー', '~': 'ー', '　': ' '}
    replace_dict = str.maketrans(dict(zen2han, **etc_sym))

    # 全角(アルファベット & 一部の記号) -> 半角 + 一部記号変換 + 不要な文字の大部分を除去
    def preprocess(comment):
        result = comment.translate(replace_dict)

        def judge_mojicode(i):
            flg = any([
                (symbol_s <= i <= symbol_e),
                (Alphabet_s <= i <= Alphabet_e or alphabet_s <= i <= alphabet_e),
                (Hiragana_s <= i <= Hiragana_e),
                (Katakana_s <= i <= Katakana_e or katakana_s <= i <= katakana_e),
                (Kanji_s <= i <= Kanji_e),
                (i in exceptions)
            ])
            return flg

        result = ''.join([s for s in result if judge_mojicode(ord(s))])

        return result

    comments = [preprocess(comment) for comment in comments]
    comments = [comment for comment in comments if len(comment) > 1]

    if pos == '名詞':
        pdir = '/'.join(__file__.split('/')[:-2])+'/'
        with open(pdir+'data/chr.yaml', mode='rb') as f:
            chrs = yaml.load(f, Loader=yaml.SafeLoader)

        with open(pdir+'data/exclude_noun.yaml', mode='rb') as f:
            exclude_noun = yaml.load(f, Loader=yaml.SafeLoader)

        kanas = chrs['hiraganas']+chrs['katakanas']+chrs['hankanas']
        alphabets = chrs['Alphabets']+chrs['alphabets']

        units = exclude_noun.pop('units')
        slang = exclude_noun.pop('slang')
        n_chrs = exclude_noun.pop('n_chrs')

        elems = [v for v in exclude_noun.values()] + [kanas, alphabets]
        tmp = []
        _ = [tmp.extend(elem) for elem in elems]
        exclude_noun = tmp

        results = []
        for comment in comments:
            if comment not in slang:
                result = tokenize(comment)
                results.extend(result)

        tmp = []
        while len(results) > 1:
            if results[1] in units:
                # n + 単位で表せるものは連結
                if results[0].isdigit():
                    k = results.pop(0)
                elif kanji2int(results[0]) > 0:
                    k = str(kanji2int(results.pop(0)))
                else:
                    k = False

                # さらに n 回目などと表せるものは連結
                if k and len(results) > 1 and results[1] in [
                    '目', '分', '前', '後', '以内', '以上', '以下' '未満', '強', '弱'
                ]:
                    tmp.append(k+results.pop(0)+results.pop(0))
                elif k:
                    tmp.append(k+results.pop(0))
                else:
                    tmp.append(results.pop(0))

            else:
                tmp.append(results.pop(0))

        if results:
            tmp.append(results.pop(0))

        results = tmp

        # 1 や 三 など 1 文字の数字は除去
        results = [
            result for result in results
            if not len(result) == 1
            or (not result.isdigit() and kanji2int(result) == 0)
        ]

    return results


def comments2vec(comments: list, model, tokenizer: str = 'janome'):
    exclude_pos0 = [] #['助詞', '助動詞', '接頭詞', '接続詞', '連体詞', '記号', 'フィラー']
    exclude_pos1 = [] #['代名詞', '接尾', '非自立', '数']
    if tokenizer == 'janome':
        from janome.tokenizer import Tokenizer
        tokenizer = Tokenizer()

        def tokenize(comment):
            result = [
                # token.base_form
                token.surface
                for token in tokenizer.tokenize(comment)
                if token.part_of_speech.split(',')[0] not in exclude_pos0
                and token.part_of_speech.split(',')[1] not in exclude_pos1
                #if not all([(s in n_chrs) for s in token.base_form])
            ]
            return [w for w in result if w]

    elif tokenizer == 'sudachi':
        from sudachipy import dictionary, tokenizer
        tokenizer_obj = dictionary.Dictionary().create()

        def tokenize(comment):
            result = [
                # token.dictionary_form()
                token.surface()
                for token in tokenizer_obj.tokenize(
                    comment, mode=tokenizer.Tokenizer.SplitMode.C
                )
                if token.part_of_speech()[0] in exclude_pos0
                and token.part_of_speech()[1] not in exclude_pos1
                #if not all([(s in n_chrs) for s in token.surface()])
            ]
            return [w for w in result if w]

    symbol_s, symbol_e = 44, 57
    Alphabet_s, Alphabet_e = 65, 90
    alphabet_s, alphabet_e = 97, 122
    Hiragana_s, Hiragana_e = 12353, 12438
    Katakana_s, Katakana_e = 12449, 12534
    katakana_s, katakana_e = 65382, 65439
    Kanji_s, Kanji_e = 19968, 40959
    exceptions = [
        32,  # ' '
        37,  # '%'
        12289,  # '、'
        12290,  # '。'
        12540   # 'ー'
    ]

    zen2han = {chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}
    etc_sym = {'〜': 'ー', '~': 'ー', '　': ' '}
    replace_dict = str.maketrans(dict(zen2han, **etc_sym))

    # 全角(アルファベット & 一部の記号) -> 半角 + 一部記号変換 + 不要な文字の大部分を除去
    def preprocess(comment):
        result = comment.translate(replace_dict)

        def judge_mojicode(i):
            flg = any([
                (symbol_s <= i <= symbol_e),
                (Alphabet_s <= i <= Alphabet_e or alphabet_s <= i <= alphabet_e),
                (Hiragana_s <= i <= Hiragana_e),
                (Katakana_s <= i <= Katakana_e or katakana_s <= i <= katakana_e),
                (Kanji_s <= i <= Kanji_e),
                (i in exceptions)
            ])
            return flg

        result = ''.join([s for s in result if judge_mojicode(ord(s))])

        return result if len(result) >= 10 else None

    def text2vec(comment, model):
        vec = model.infer_vector([
            token
            for token in tokenize(preprocess(comment))
            if token
        ])
        return vec

    comments = [preprocess(comment) for comment in comments]
    comments = [comment for comment in comments if comment]
    text = ' '.join(comments)

    if text:
        vec = text2vec(text, model)
        w = len(comments)

        return w, vec
    else:
        return None, None
