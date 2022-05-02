import tkinter as tk
from tkinter import ttk
import ttkthemes
from PIL import Image, ImageTk
from wordcloud import WordCloud
import pandas as pd
import webbrowser
from tqdm.tk import tqdm as tqdm_tk

from nico_info import NicovideoInfomation
from utils.parser import fetch_ranking_info, fetch_video_info, url2img
from utils.nlp import analyze_comments


genres_dict = {
    '全ジャンル': 'all',
    '話題': 'hot-topic',
    'エンターテインメント': 'entertainment',
    'ラジオ': 'radio',
    '音楽・サウンド': 'music_sound',
    'ダンス': 'dance',
    '動物': 'animal',
    '自然': 'nature',
    '料理': 'cooking',
    '旅行・アウトドア': 'traveling_outdoor',
    '乗り物': 'vehicle',
    'スポーツ': 'sports',
    '社会・政治・時事': 'society_politics_news',
    '技術・工作': 'technology_craft',
    '解説・講座': 'commentary_lecture',
    'アニメ': 'anime',
    'ゲーム': 'game',
    'その他': 'other',
    'R-18': 'r18'
}
genres_dict = {
    k: 'genre/'+v if k != '話題' else v for k, v in genres_dict.items()
}

terms_dict = {
    '毎時': 'hour',
    '24時間': '24h',
    '週間': 'week',
    '月間': 'month',
    '全期間': 'total'
}

PANE1_W = 600
PANE2_W = 1000

WORDCLOUD_W = 600
WORDCLOUD_H = 350


class Application(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.master.title("NicoVideoCommentAnalysis")

        # pane1
        pane1_frame = ttk.Frame(self.master, width=PANE1_W)
        # pane2
        pane2_frame = ttk.Frame(self.master, width=PANE2_W)
        notebook = ttk.Notebook(pane2_frame)

        pane1_frame.pack(side=tk.LEFT)
        pane2_frame.pack(side=tk.LEFT, fill=tk.Y)

        # style
        style = ttk.Style()
        style.theme_use('black')
        style.configure(
            'Ranking.TButton',
            anchor="w", borderwidth=0, justify='LEFT', wraplength=330
        )
        style.configure(
            'Card.TButton',
            anchor="w", borderwidth=0, justify='LEFT', wraplength=550
        )

        # insrtance var
        # dummy
        self.card_dict = {
            'url': '',
            'title': '',
            'thumbnail': 'https://nicovideo.cdn.nimg.jp/web/img/common/video_deleted.jpg',
            'post': '',
            'view': '',
            'comment': '',
            'like': '',
            'mylist': ''
        }
        self.comments_df = pd.DataFrame(
            columns=[
                'comment_id', 'comment', 'user_id', 'write_time', 'video_time',
                '184', 'position', 'size', 'color', 'command', 'score'
            ]
        ).set_index('comment_id')

        self.p1_frame = pane1_frame
        self.p2_frame = pane2_frame

        self.notebook = notebook

        self.c_button = None
        self.rv_buttons = None

        self.pane1_set()
        self.pane2_set()

    def pane1_set(self):
        self.input_panel_set()
        self.ranking_panel_set()

    def pane2_set(self):
        self.notebook_set()
        self.control_panel_set()
        self.card_view()
        self.comment_view()

    def notebook_set(self):
        comment_load_tab = ttk.Frame(self.notebook)
        comment_tab = ttk.Frame(self.notebook)
        wordcloud_tab = ttk.Frame(self.notebook)

        self.notebook.add(comment_load_tab, text='読み込み/抽出')
        self.notebook.add(comment_tab, text='コメント')
        self.notebook.add(wordcloud_tab, text='WordCloud')

        self.notebook.grid(row=1, column=0)

    def input_panel_set(self):
        # input frame
        input_frame = ttk.Frame(self.p1_frame)

        vid = tk.StringVar()
        vid_label = ttk.Label(input_frame, text='動画ID')
        vid_entry = ttk.Entry(
            input_frame,
            textvariable=vid,
            width=35
        )

        def vid_click_callback():
            url = f'https://www.nicovideo.jp/watch/{vid.get()}'
            self.card_dict = fetch_video_info(url)
            _ = self.card_view()

        vid_button = ttk.Button(
            input_frame,
            text='OK',
            width=5,
            command=vid_click_callback
        )
        vid_label.grid(row=0, column=0, sticky=tk.W)
        vid_entry.grid(row=0, column=1, sticky=tk.EW)
        vid_button.grid(row=0, column=2, sticky=tk.E)

        vurl = tk.StringVar()
        vurl_label = ttk.Label(input_frame, text='動画URL')
        vurl_entry = ttk.Entry(
            input_frame,
            textvariable=vurl,
            width=35
        )

        def vurl_click_callback():
            url = vurl.get()
            self.card_dict = fetch_video_info(url)
            self.card_view()

        vurl_button = ttk.Button(
            input_frame,
            text='OK',
            width=5,
            command=vurl_click_callback
        )
        vurl_label.grid(row=1, column=0, sticky=tk.W)
        vurl_entry.grid(row=1, column=1, sticky=tk.EW)
        vurl_button.grid(row=1, column=2, sticky=tk.E)

        input_frame.grid(row=0, column=0)

    def ranking_panel_set(self):
        ranking_frame = ttk.Frame(self.p1_frame)

        genre = tk.StringVar()
        genres_combobox = ttk.Combobox(
            ranking_frame,
            textvariable=genre,
            values=list(genres_dict.keys()),
            width=15,
            state='readonly'
        )
        genres_combobox.current(0)

        term = tk.StringVar()
        terms_combobox = ttk.Combobox(
            ranking_frame,
            textvariable=term,
            values=list(terms_dict.keys()),
            width=5,
            state='readonly'
        )
        terms_combobox.current(0)

        confirm_button = ttk.Button(
            ranking_frame,
            text='ランキング取得',
            width=10,
            command=self.ranking_view
        )

        rviewer_frame = ttk.Frame(ranking_frame)
        rviewer_canvas = tk.Canvas(
            rviewer_frame, width=420, height=800, bd=0
        )
        rviewer_canvas.pack(side=tk.LEFT)

        rviewer_scrollbar = ttk.Scrollbar(
            rviewer_frame, orient=tk.VERTICAL, command=rviewer_canvas.yview
        )
        rviewer_scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        rviewer_canvas['yscrollcommand'] = rviewer_scrollbar.set
        rviewer_canvas.yview_moveto(0)

        size_y = 100 * 50
        rviewer_canvas.config(scrollregion=(0, 0, 0, size_y))

        rvc_frame = tk.Frame(rviewer_canvas)
        rviewer_canvas.create_window(
            (0, 0),
            window=rvc_frame, anchor=tk.NW, width=rviewer_canvas.cget('width')
        )

        genres_combobox.grid(row=0, column=0)
        terms_combobox.grid(row=0, column=1)
        confirm_button.grid(row=0, column=2)
        rviewer_frame.grid(row=1, columnspan=3)

        ranking_frame.grid(row=1, column=0)

        self.genre = genre
        self.term = term
        self.rvc_frame = rvc_frame

    def control_panel_set(self):
        notebook = self.notebook

        # --- load ---
        load_frame = ttk.LabelFrame(
            notebook.nametowidget(notebook.tabs()[0]),
            text='コメント読み込み', relief=tk.RIDGE, padding=[10, 10, 10, 10]
        )

        load_opt_frame = ttk.LabelFrame(
            load_frame, text='options', relief=tk.RIDGE,
            padding=[10, 10, 10, 10]
        )

        lfork_opt_frame = ttk.LabelFrame(
            load_opt_frame, text='コメントの種類', labelanchor=tk.NW,
            padding=[5, 5, 5, 5]
        )
        lfork0 = tk.BooleanVar(); lfork0.set(True)
        lfork0_checkbutton = ttk.Checkbutton(
            lfork_opt_frame, variable=lfork0, text='一般コメント'
        )
        lfork1 = tk.BooleanVar(); lfork1.set(True)
        lfork1_checkbutton = ttk.Checkbutton(
            lfork_opt_frame, variable=lfork1, text='投稿者コメント'
        )
        lfork2 = tk.BooleanVar(); lfork2.set(True)
        lfork2_checkbutton = ttk.Checkbutton(
            lfork_opt_frame, variable=lfork2, text='かんたんコメント'
        )

        mode_opt_frame = ttk.LabelFrame(
            load_opt_frame, text='mode', labelanchor=tk.NW,
            padding=[5, 5, 5, 5]
        )
        mode = tk.StringVar(value='once')
        once_radiobutton = ttk.Radiobutton(
            mode_opt_frame,
            text='once',
            value='once',
            variable=mode
        )
        roughly_radiobutton = ttk.Radiobutton(
            mode_opt_frame,
            text='roughly',
            value='roughly',
            variable=mode
        )
        exactly_radiobutton = ttk.Radiobutton(
            mode_opt_frame,
            text='exactly',
            value='exactly',
            variable=mode
        )

        hop_rate_opt_frame = ttk.LabelFrame(
            load_opt_frame, text='hop rate', labelanchor=tk.NW,
            padding=[5, 5, 5, 5]
        )
        hop_rate_val = ttk.Label(
            hop_rate_opt_frame,
            text='hop rate',
            width=4,
            relief=tk.SUNKEN,
        )

        def set_label(value):
            hop_rate_val['text'] = str(round(float(value), 2))

        hop_rate = tk.DoubleVar(value=.1)
        hop_rate_scale = ttk.Scale(
            hop_rate_opt_frame,
            orient=tk.HORIZONTAL,
            variable=hop_rate,
            from_=.1,
            to=.9,
            length=130,
            command=set_label
        )
        hop_rate_scale.set(.2)

        def cl_click_callback():
            options = {
                'forks': [i for i, fork in enumerate([lfork0, lfork1, lfork2]) if fork.get()],
                'mode': mode.get(),
                'hop_rate': hop_rate.get()
            }

            self.comment_load(**options)
            self.comment_view()
            self.wordcloud_generate()
            self.wordcloud_view()
        
        lbuttons_frame = ttk.Frame(
            load_frame, padding=[10, 10, 10, 10]
        )

        load_button = ttk.Button(
            lbuttons_frame,
            text='load', padding=[0, 0, 0], width=20,
            command=cl_click_callback
        )

        load_frame.grid(row=0, column=0, padx=10, pady=10)

        load_opt_frame.grid(row=0, column=0, padx=10, pady=10)

        lfork_opt_frame.grid(row=0, column=0)
        lfork0_checkbutton.grid(row=0, column=0)
        lfork1_checkbutton.grid(row=0, column=1)
        lfork2_checkbutton.grid(row=0, column=2)

        mode_opt_frame.grid(row=1, column=0, sticky=tk.W)
        once_radiobutton.grid(row=0, column=0)
        roughly_radiobutton.grid(row=0, column=1)
        exactly_radiobutton.grid(row=0, column=2)

        hop_rate_opt_frame.grid(row=2, column=0, sticky=tk.W)
        hop_rate_scale.grid(row=0, column=0)
        hop_rate_val.grid(row=0, column=1)

        lbuttons_frame.grid(row=0, column=1, padx=10, pady=10)
        load_button.grid(row=0, column=0)

        # --- extract ---
        extract_frame = ttk.LabelFrame(
            notebook.nametowidget(notebook.tabs()[0]),
            text='コメント抽出', relief=tk.RIDGE, padding=[10, 10, 10, 10]
        )
        extract_opt_frame = ttk.LabelFrame(
            extract_frame, text='options', relief=tk.RIDGE,
            padding=[10, 10, 10, 10]
        )
        efork_opt_frame = ttk.LabelFrame(
            extract_opt_frame, text='コメントの種類', labelanchor=tk.NW,
            padding=[5, 5, 5, 5]
        )
        efork0 = tk.BooleanVar(); efork0.set(True)
        efork0_checkbutton = ttk.Checkbutton(
            efork_opt_frame, variable=efork0, text='一般コメント'
        )
        efork1 = tk.BooleanVar(); efork1.set(True)
        efork1_checkbutton = ttk.Checkbutton(
            efork_opt_frame, variable=efork1, text='投稿者コメント'
        )
        efork2 = tk.BooleanVar(); efork2.set(True)
        efork2_checkbutton = ttk.Checkbutton(
            efork_opt_frame, variable=efork2, text='かんたんコメント'
        )

        extract_frame.grid(row=1, column=0, padx=10, pady=10)
        
        extract_opt_frame.grid(row=0, column=0)
        
        efork_opt_frame.grid(row=0, column=0)
        efork0_checkbutton.grid(row=0, column=0)
        efork1_checkbutton.grid(row=0, column=1)
        efork2_checkbutton.grid(row=0, column=2)

    def ranking_view(self):
        if self.rv_buttons:
            _ = [button.destroy() for button in self.rv_buttons]

        genre_key = genres_dict[str(self.genre.get())]
        term_key = terms_dict[str(self.term.get())]
        url = f'https://www.nicovideo.jp/ranking/{genre_key}?term={term_key}'
        info_dict = fetch_ranking_info(url)
        self.ranking_info = info_dict

        def rviewer_click_callback(i):
            def x():
                self.card_dict = self.ranking_info[(i, )[0]]
                _ = self.card_view()
            return x

        rviewer_buttons = []
        with tqdm_tk(info_dict.items()) as pbar:
            for i, d in pbar:
                thumbnail = url2img(d['thumbnail'])
                thumbnail = ImageTk.PhotoImage(thumbnail.resize((63, 47)))
                if len(d['title']) < 50:
                    title = d['title']
                else:
                    title = d['title'][:50] + '…'

                text = f'{title}\n▶️{d["view"]}💬{d["comment"]}🤍{d["like"]}📁{d["mylist"]}🕛{d["post"]}'
                callback = lambda: rviewer_click_callback(i)
                card_button = ttk.Button(
                    self.rvc_frame,
                    text=text, padding=[0, 0, 0], width=630,
                    style='Ranking.TButton', compound='left',
                    image=thumbnail,
                    command=callback()
                )
                card_button.photo = thumbnail
                card_button.pack()
                rviewer_buttons.append(card_button)

                pbar._tk_window.update()
            pbar._tk_window.destroy()

        self.rv_buttons = rviewer_buttons

    def card_view(self):
        if self.c_button:
            self.c_button.destroy()

        d = self.card_dict
        if len(d['title']) < 90:
            title = d['title']
        else:
            title = d['title'][:90] + '…'
        text = f'{title}\n▶️{d["view"]}💬{d["comment"]}🤍{d["like"]}📁{d["mylist"]}🕛{d["post"]}'
        thumbnail = url2img(d['thumbnail'])
        thumbnail = ImageTk.PhotoImage(thumbnail.resize((93, 70)))

        card_button = ttk.Button(
            self.p2_frame,
            text=text, padding=[0, 0, 0], width=60,
            style='Card.TButton', compound='left',
            image=thumbnail,
            command=lambda: webbrowser.open(d['url'])
        )
        card_button.photo = thumbnail
        card_button.grid(row=0, column=0, sticky=tk.NW)

        self.c_button = card_button

    def comment_view(self):
        df = self.comments_df.reset_index().sort_values('write_time')
        df = df.rename(
            columns={
                'comment_id': 'cid', 'user_id': 'uid',
                'write_time': 'wtime', 'video_time': 'vtime'
            }
        )
        df = df.drop(['184', 'position', 'size', 'color', 'command'], axis=1)
        df_width = {
            'cid': 50,
            'comment': 260,
            'uid': 90,
            'wtime': 90,
            'vtime': 60,
            '184': 20,
            'position': 50,
            'size': 50,
            'color': 50,
            'command': 50,
            'score': 50
        }
        notebook = self.notebook
        tree = ttk.Treeview(
            notebook.nametowidget(notebook.tabs()[1]),
            columns=list(df.columns), height=35
        )
        for i in range(len(df)):
            values = [df.iloc[i][j] for j in range(len(df.columns))]
            tree.insert('', 'end', values=values)
            # tree.column(i, wi)
        tree["show"] = "headings"
        _ = [
            (
                tree.heading(i, text=c),
                tree.column(c, width=df_width[c], stretch=False)
            )
            for i, c in enumerate(df.columns)
        ]

        tree.grid(row=2, column=0)

    def wordcloud_view(self):
        notebook = self.notebook
        wordcloud_canvas = tk.Canvas(
            notebook.nametowidget(notebook.tabs()[2]),
            width=WORDCLOUD_W,
            height=WORDCLOUD_H
            #relief=tk.RIDGE  # 枠線を表示
            # 枠線の幅を設定
        )

        wordcloud = Image.open('./wordcloud.png')
        wordcloud = ImageTk.PhotoImage(wordcloud)
        wordcloud_canvas.create_image(  # キャンバス上にイメージを配置
            0,  # x座標
            0,  # y座標
            image=wordcloud,  # 配置するイメージオブジェクトを指定
            anchor=tk.NW
        )
        wordcloud_canvas.photo = wordcloud
        wordcloud_canvas.grid(row=0, column=0)

    def comment_load(self, **options):
        ninfo = NicovideoInfomation(video_url=self.card_dict['url'])
        ninfo.load_comments(**options)
        comments_df = ninfo.comments_df

        self.comments_df = comments_df

    def wordcloud_generate(self):
        df = self.comments_df[self.comments_df.index.str[0] == '0']
        comments = df.comment
        results = analyze_comments(comments, tokenizer='janome')
        text = ' '.join(results)

        font_path = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
        wordcloud = WordCloud(
            background_color='white',
            font_path=font_path,
            width=WORDCLOUD_W,
            height=WORDCLOUD_H,
            max_words=500
        ).generate(text)

        wordcloud.to_file('./wordcloud.png')


def main():
    win = ttkthemes.ThemedTk()
    app = Application(master=win)
    app.mainloop()


if __name__ == "__main__":
    main()