import tkinter as tk
from tkinter import ttk
import ttkthemes
import pandas as pd
import webbrowser
from PIL import Image, ImageTk
from wordcloud import WordCloud
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

PANE1_W = 700
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
        # tabs
        tabs_notebook = ttk.Notebook(pane2_frame)

        pane1_frame.pack(side=tk.LEFT, anchor=tk.N)
        pane2_frame.pack(side=tk.LEFT, anchor=tk.N, fill=tk.Y)

        # style
        style = ttk.Style()
        style.theme_use('black')
        style.configure(
            'Ranking.TButton',
            anchor='w', borderwidth=0, justify='LEFT', wraplength=350
        )
        style.configure(
            'Card.TButton',
            anchor='w', borderwidth=0, justify='LEFT', wraplength=550
        )
        style.configure('White.TCheckbutton',   foreground='#FFFFFF')
        style.configure('Red.TCheckbutton',     foreground='#FF0000')
        style.configure('Pink.TCheckbutton',    foreground='#FF8080')
        style.configure('Orange.TCheckbutton',  foreground='#FFC000')
        style.configure('Yellow.TCheckbutton',  foreground='#FFFF00')
        style.configure('Green.TCheckbutton',   foreground='#00FF00')
        style.configure('Cyan.TCheckbutton',    foreground='#00FFFF')
        style.configure('Blue.TCheckbutton',    foreground='#0000FF')
        style.configure('Purple.TCheckbutton',  foreground='#C000FF')
        style.configure('Black.TCheckbutton',   foreground='#000000')
        style.configure('White2.TCheckbutton',  foreground='#CCCC99')
        style.configure('Red2.TCheckbutton',    foreground='#CC0033')
        style.configure('Pink2.TCheckbutton',   foreground='#FF33CC')
        style.configure('Orange2.TCheckbutton', foreground='#FF6600')
        style.configure('Yellow2.TCheckbutton', foreground='#999900')
        style.configure('Green2.TCheckbutton',  foreground='#00CC66')
        style.configure('Cyan2.TCheckbutton',   foreground='#00CCCC')
        style.configure('Blue2.TCheckbutton',   foreground='#3399FF')
        style.configure('Purple2.TCheckbutton', foreground='#6633CC')
        style.configure('Black2.TCheckbutton',  foreground='#666666')


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

        self.pane1_frame = pane1_frame
        self.pane2_frame = pane2_frame

        self.tabs_notebook = tabs_notebook

        self.rviewer_buttons = None
        self.card_button = None
        self.comment_treeview = None
        self.wordcloud_canvas = None

        self.pane1_set()
        self.pane2_set()

    def pane1_set(self):
        self.input_panel_set()
        self.ranking_panel_set()

    def pane2_set(self):
        self.tabs_set()
        self.control_tab_set()

        self.card_view()
        self.comment_view()

    def input_panel_set(self):
        # === panel frame ===
        panel_frame = ttk.Frame(self.pane1_frame)

        # === Video ID ===
        vid_var = tk.StringVar()
        vid_label = ttk.Label(panel_frame, text='動画ID')
        vid_entry = tk.Entry(panel_frame, textvariable=vid_var, width=35)

        def vid_click_callback():
            url = f'https://www.nicovideo.jp/watch/{vid_var.get()}'
            self.card_dict = fetch_video_info(url)
            self.card_view()

        vid_button = ttk.Button(
            panel_frame,
            text='OK', command=vid_click_callback,
            width=5
        )

        # === Video URL ===
        vurl_var = tk.StringVar()
        vurl_label = ttk.Label(panel_frame, text='動画URL')
        vurl_entry = tk.Entry(panel_frame, textvariable=vurl_var, width=35)

        def vurl_click_callback():
            url = vurl_var.get()
            self.card_dict = fetch_video_info(url)
            self.card_view()

        vurl_button = ttk.Button(
            panel_frame,
            text='OK', command=vurl_click_callback,
            width=5
        )

        # === place ===
        panel_frame.grid(row=0, column=0)

        vid_label.grid(row=0, column=0, sticky=tk.W)
        vid_entry.grid(row=0, column=1, sticky=tk.EW)
        vid_button.grid(row=0, column=2, sticky=tk.E)

        vurl_label.grid(row=1, column=0, sticky=tk.W)
        vurl_entry.grid(row=1, column=1, sticky=tk.EW)
        vurl_button.grid(row=1, column=2, sticky=tk.E)

    def ranking_panel_set(self):
        # === panel frame ===
        panel_frame = ttk.Frame(self.pane1_frame)

        # === genre ===
        genre_var = tk.StringVar()
        genres_combobox = ttk.Combobox(
            panel_frame,
            textvariable=genre_var, values=list(genres_dict.keys()),
            state='readonly',
            width=15
        )

        genres_combobox.current(0)

        # === term ===
        term_var = tk.StringVar()
        terms_combobox = ttk.Combobox(
            panel_frame,
            textvariable=term_var, values=list(terms_dict.keys()),
            state='readonly',
            width=5
        )

        terms_combobox.current(0)

        select_button = ttk.Button(
            panel_frame,
            text='ランキング取得', command=self.ranking_view,
            width=10
        )

        # === ranking viewer ===
        viewer_frame = ttk.Frame(panel_frame)
        viewer_canvas = tk.Canvas(
            viewer_frame,
            width=420, height=800, bd=0
        )
        viewer_scrollbar = ttk.Scrollbar(
            viewer_frame,
            command=viewer_canvas.yview,
            orient=tk.VERTICAL,
        )

        viewer_canvas.yview_moveto(0)
        viewer_canvas['yscrollcommand'] = viewer_scrollbar.set
        viewer_canvas.config(scrollregion=(0, 0, 0, 0))

        cards_frame = tk.Frame(viewer_canvas)

        viewer_canvas.create_window(
            (0, 0),
            window=cards_frame,
            anchor=tk.NW,
            width=viewer_canvas.cget('width')
        )

        panel_frame.grid(row=1, column=0)

        genres_combobox.grid(row=0, column=0)
        terms_combobox.grid(row=0, column=1)
        select_button.grid(row=0, column=2)

        viewer_frame.grid(row=1, columnspan=3)
        viewer_canvas.pack(side=tk.LEFT)
        viewer_scrollbar.pack(side=tk.LEFT, fill=tk.Y)

        self.genre = genre_var
        self.term = term_var
        self.rcards_frame = cards_frame
        self.rviewer_canvas = viewer_canvas


    def tabs_set(self):
        control_tab = ttk.Frame(self.tabs_notebook)
        comment_tab = ttk.Frame(self.tabs_notebook)
        wordcloud_tab = ttk.Frame(self.tabs_notebook)

        self.tabs_notebook.add(control_tab, text='読み込み/抽出')
        self.tabs_notebook.add(comment_tab, text='コメント')
        self.tabs_notebook.add(wordcloud_tab, text='WordCloud')

        self.tabs_notebook.grid(row=1, column=0)


    def control_tab_set(self):
        notebook = self.tabs_notebook
        tab_frame = notebook.nametowidget(notebook.tabs()[0])

        # === load ===
        def load_set():
            load_frame = ttk.LabelFrame(
                tab_frame,
                text='コメント読み込み', relief=tk.RIDGE,
                padding=[10, 10, 10, 10]
            )
            opt_frame = ttk.LabelFrame(
                load_frame, text='options', relief=tk.RIDGE,
                padding=[10, 10, 10, 10]
            )

            forks_frame = ttk.LabelFrame(
                opt_frame,
                text='コメントの種類', labelanchor=tk.NW,
                padding=[5, 5, 5, 5]
            )
            fork0_var = tk.BooleanVar(); fork0_var.set(True)
            fork0_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork0_var, text='一般コメント'
            )
            fork1_var = tk.BooleanVar(); fork1_var.set(True)
            fork1_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork1_var, text='投稿者コメント'
            )
            fork2_var = tk.BooleanVar(); fork2_var.set(True)
            fork2_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork2_var, text='かんたんコメント'
            )

            mode_frame = ttk.LabelFrame(
                opt_frame, text='mode', labelanchor=tk.NW,
                padding=[5, 5, 5, 5]
            )
            mode_var = tk.StringVar(value='once')
            once_radiobutton = ttk.Radiobutton(
                mode_frame, text='once', value='once', variable=mode_var
            )
            roughly_radiobutton = ttk.Radiobutton(
                mode_frame, text='roughly', value='roughly', variable=mode_var
            )
            exactly_radiobutton = ttk.Radiobutton(
                mode_frame, text='exactly', value='exactly', variable=mode_var
            )

            hoprate_frame = ttk.LabelFrame(
                opt_frame, text='hop rate', labelanchor=tk.NW,
                padding=[5, 5, 5, 5]
            )
            hoprate_label = ttk.Label(
                hoprate_frame,
                text='hop rate', relief=tk.SUNKEN,
                width=4
            )

            def set_hoprate_label(value):
                hoprate_label['text'] = str(round(float(value), 2))

            hoprate_val = tk.DoubleVar(value=.1)
            hoprate_scale = ttk.Scale(
                hoprate_frame,
                variable=hoprate_val, command=set_hoprate_label,
                from_=.1, to=.9,
                orient=tk.HORIZONTAL,
                length=130,
            )
            hoprate_scale.set(.2)

            def load_click_callback():
                forks = [fork0_var, fork1_var, fork2_var]
                options = {
                    'forks': [i for i, fork in enumerate(forks) if fork.get()],
                    'mode': mode_var.get(),
                    'hop_rate': hoprate_val.get()
                }

                self.comment_load(**options)
                self.comment_view()
                # self.wordcloud_generate()
                # self.wordcloud_view()

                for button in self.ebuttons_frame.winfo_children():
                    button['state'] = 'enable'

            buttons_frame = ttk.Frame(load_frame, padding=[10, 10, 10, 10])

            load_button = ttk.Button(
                buttons_frame,
                text='load', command=load_click_callback,
                padding=[0, 0, 0], width=20,

            )

            load_frame.grid(row=0, column=0, padx=10, pady=10)

            opt_frame.grid(row=0, column=0, padx=10, pady=10)

            forks_frame.grid(row=0, column=0, sticky=tk.EW)
            fork0_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            fork1_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            fork2_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)

            mode_frame.grid(row=1, column=0, sticky=tk.EW)
            once_radiobutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            roughly_radiobutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            exactly_radiobutton.pack(side=tk.LEFT, fill=tk.X, expand=True)

            hoprate_frame.grid(row=2, column=0, sticky=tk.EW)
            hoprate_scale.grid(row=0, column=0)
            hoprate_label.grid(row=0, column=1)

            buttons_frame.grid(row=0, column=1, padx=10, pady=10)
            load_button.grid(row=0, column=0)

        load_set()

        # === extract ===
        def extract_set():
            extract_frame = ttk.LabelFrame(
                tab_frame,
                text='コメント抽出', relief=tk.RIDGE, padding=[10, 10, 10, 10]
            )

            opt_frame = ttk.LabelFrame(
                extract_frame, text='options', relief=tk.RIDGE,
                padding=[10, 10, 10, 10]
            )

            forks_frame = ttk.LabelFrame(
                opt_frame, text='コメントの種類', labelanchor=tk.NW,
                padding=[5, 5, 5, 5]
            )
            fork0_var = tk.BooleanVar(); fork0_var.set(True)
            fork0_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork0_var, text='一般コメント'
            )
            fork1_var = tk.BooleanVar(); fork1_var.set(True)
            fork1_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork1_var, text='投稿者コメント'
            )
            fork2_var = tk.BooleanVar(); fork2_var.set(True)
            fork2_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork2_var, text='かんたんコメント'
            )

            comment_frame = ttk.LabelFrame(
                opt_frame, text='コメント', labelanchor=tk.NW,
                padding=[5, 5, 5, 5]
            )
            comment_var = tk.StringVar()
            comment_entry = tk.Entry(comment_frame, textvariable=comment_var)

            uid_frame = ttk.LabelFrame(
                opt_frame, text='ユーザーID', labelanchor=tk.NW,
                padding=[5, 5, 5, 5]
            )
            uid_var = tk.StringVar()
            uid_entry = tk.Entry(uid_frame, textvariable=uid_var)

            position_frame = ttk.LabelFrame(
                opt_frame, text='コメントの位置 (デフォルト：中)', labelanchor=tk.NW,
                padding=[5, 5, 5, 5]
            )
            ue_var = tk.BooleanVar(); ue_var.set(True)
            ue_checkbutton = ttk.Checkbutton(
                position_frame, variable=ue_var, text='上'
            )
            naka_var = tk.BooleanVar(); naka_var.set(True)
            naka_checkbutton = ttk.Checkbutton(
                position_frame, variable=naka_var, text='中'
            )
            shita_var = tk.BooleanVar(); shita_var.set(True)
            shita_checkbutton = ttk.Checkbutton(
                position_frame, variable=shita_var, text='下'
            )

            size_frame = ttk.LabelFrame(
                opt_frame, text='コメントの大きさ (デフォルト：中)', labelanchor=tk.NW,
                padding=[5, 5, 5, 5]
            )
            big_var = tk.BooleanVar(); big_var.set(True)
            big_checkbutton = ttk.Checkbutton(
                size_frame, variable=big_var, text='大'
            )
            medium_var = tk.BooleanVar(); medium_var.set(True)
            medium_checkbutton = ttk.Checkbutton(
                size_frame, variable=medium_var, text='中'
            )
            small_var = tk.BooleanVar(); small_var.set(True)
            small_checkbutton = ttk.Checkbutton(
                size_frame, variable=small_var, text='小'
            )

            color_frame = ttk.LabelFrame(
                opt_frame, text='コメントの色', labelanchor=tk.NW,
                padding=[5, 5, 5, 5]
            )
            general_frame = ttk.Frame(color_frame)
            white_var = tk.BooleanVar(); white_var.set(True)
            white_checkbutton = ttk.Checkbutton(
                general_frame, variable=white_var, text='■', style='White.TCheckbutton'
            )
            red_var = tk.BooleanVar(); red_var.set(True)
            red_checkbutton = ttk.Checkbutton(
                general_frame, variable=red_var, text='■', style='Red.TCheckbutton'
            )
            pink_var = tk.BooleanVar(); pink_var.set(True)
            pink_checkbutton = ttk.Checkbutton(
                general_frame, variable=pink_var, text='■', style='Pink.TCheckbutton'
            )
            orange_var = tk.BooleanVar(); orange_var.set(True)
            orange_checkbutton = ttk.Checkbutton(
                general_frame, variable=orange_var, text='■', style='Orange.TCheckbutton'
            )
            yellow_var = tk.BooleanVar(); yellow_var.set(True)
            yellow_checkbutton = ttk.Checkbutton(
                general_frame, variable=yellow_var, text='■', style='Yellow.TCheckbutton'
            )
            green_var = tk.BooleanVar(); green_var.set(True)
            green_checkbutton = ttk.Checkbutton(
                general_frame, variable=green_var, text='■', style='Green.TCheckbutton'
            )
            cyan_var = tk.BooleanVar(); cyan_var.set(True)
            cyan_checkbutton = ttk.Checkbutton(
                general_frame, variable=cyan_var, text='■', style='Cyan.TCheckbutton'
            )
            blue_var = tk.BooleanVar(); blue_var.set(True)
            blue_checkbutton = ttk.Checkbutton(
                general_frame, variable=blue_var, text='■', style='Blue.TCheckbutton'
            )
            purple_var = tk.BooleanVar(); purple_var.set(True)
            purple_checkbutton = ttk.Checkbutton(
                general_frame, variable=purple_var, text='■', style='Purple.TCheckbutton'
            )
            black_var = tk.BooleanVar(); black_var.set(True)
            black_checkbutton = ttk.Checkbutton(
                general_frame, variable=black_var, text='■', style='Black.TCheckbutton'
            )
            premium_frame = ttk.Frame(color_frame)
            white2_var = tk.BooleanVar(); white2_var.set(True)
            white2_checkbutton = ttk.Checkbutton(
                premium_frame, variable=white2_var, text='■', style='White2.TCheckbutton'
            )
            red2_var = tk.BooleanVar(); red2_var.set(True)
            red2_checkbutton = ttk.Checkbutton(
                premium_frame, variable=red2_var, text='■', style='Red2.TCheckbutton'
            )
            pink2_var = tk.BooleanVar(); pink2_var.set(True)
            pink2_checkbutton = ttk.Checkbutton(
                premium_frame, variable=pink2_var, text='■', style='Pink2.TCheckbutton'
            )
            orange2_var = tk.BooleanVar(); orange2_var.set(True)
            orange2_checkbutton = ttk.Checkbutton(
                premium_frame, variable=orange2_var, text='■', style='Orange2.TCheckbutton'
            )
            yellow2_var = tk.BooleanVar(); yellow2_var.set(True)
            yellow2_checkbutton = ttk.Checkbutton(
                premium_frame, variable=yellow2_var, text='■', style='Yellow2.TCheckbutton'
            )
            green2_var = tk.BooleanVar(); green2_var.set(True)
            green2_checkbutton = ttk.Checkbutton(
                premium_frame, variable=green2_var, text='■', style='Green2.TCheckbutton'
            )
            cyan2_var = tk.BooleanVar(); cyan2_var.set(True)
            cyan2_checkbutton = ttk.Checkbutton(
                premium_frame, variable=cyan2_var, text='■', style='Cyan2.TCheckbutton'
            )
            blue2_var = tk.BooleanVar(); blue2_var.set(True)
            blue2_checkbutton = ttk.Checkbutton(
                premium_frame, variable=blue2_var, text='■', style='Blue2.TCheckbutton'
            )
            purple2_var = tk.BooleanVar(); purple2_var.set(True)
            purple2_checkbutton = ttk.Checkbutton(
                premium_frame, variable=purple2_var, text='■', style='Purple2.TCheckbutton'
            )
            black2_var = tk.BooleanVar(); black2_var.set(True)
            black2_checkbutton = ttk.Checkbutton(
                premium_frame, variable=black2_var, text='■', style='Black2.TCheckbutton'
            )

            def make_opt_dict():
                forks = [fork0_var.get(), fork1_var.get(), fork2_var.get()]
                opt_dict = {
                    'forks': [i for i, fork in enumerate(lforks) if fork.get()],
                    'user_id': None,
                    'write_time': (None, None),
                    'video_time': (None, None),
                    'position': None,
                    'size': None,
                    'color': None,
                    'score': (None, None)
                }
                return opt_dict

            def select_click_callback():
                pass

            def reset_click_callback():
                self.comments_df = self.org_df.copy()

            buttons_frame = ttk.Frame(extract_frame, padding=[10, 10, 10, 10])

            select_button = ttk.Button(
                buttons_frame,
                text='select', command=select_click_callback,
                padding=[0, 0, 0], width=20,
            )
            reset_button = ttk.Button(
                buttons_frame,
                text='reset', command=reset_click_callback,
                padding=[0, 0, 0], width=20,
            )

            select_button['state'] = reset_button['state'] = 'disable'

            extract_frame.grid(row=1, column=0, padx=10, pady=10)

            opt_frame.grid(row=0, column=0)

            forks_frame.grid(row=0, column=0, sticky=tk.EW)
            fork0_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            fork1_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            fork2_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)

            comment_frame.grid(row=1, column=0, sticky=tk.EW)
            comment_entry.grid(row=0, column=0)

            uid_frame.grid(row=2, column=0, sticky=tk.EW)
            uid_entry.grid(row=0, column=0)

            position_frame.grid(row=3, column=0, sticky=tk.EW)
            ue_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            naka_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            shita_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)

            size_frame.grid(row=4, column=0, sticky=tk.EW)
            big_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            medium_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            small_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)

            color_frame.grid(row=5, column=0, sticky=tk.EW)
            general_frame.grid(row=0, column=0, sticky=tk.EW)
            white_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            red_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            pink_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            orange_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            yellow_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            purple_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            black_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            premium_frame.grid(row=1, column=0, sticky=tk.EW)
            white2_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            red2_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            pink2_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            orange2_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            yellow2_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            purple2_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            black2_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)

            buttons_frame.grid(row=0, column=1, padx=10, pady=10)
            select_button.pack(pady=10)
            reset_button.pack(pady=10)

            self.ebuttons_frame = buttons_frame

        extract_set()

    def ranking_view(self):
        _ = [button.destroy() for button in self.rcards_frame.winfo_children()]

        genre_key = genres_dict[str(self.genre.get())]
        term_key = terms_dict[str(self.term.get())]
        url = f'https://www.nicovideo.jp/ranking/{genre_key}?term={term_key}'
        info_dict = fetch_ranking_info(url)
        self.ranking_info = info_dict

        def viewer_click_callback(i):
            def x():
                self.card_dict = self.ranking_info[(i, )[0]]
                self.card_view()
            return x

        video_text = '{title}\n▶️{view}💬{comment}💕{like}🕘{post}'
        with tqdm_tk(info_dict.items()) as pbar:
            for i, d in pbar:
                thumbnail = url2img(d['thumbnail'])
                thumbnail = ImageTk.PhotoImage(thumbnail.resize((63, 47)))
                if len(d['title']) < 50:
                    title = d['title']
                else:
                    title = d['title'][:50] + '…'

                card_button = ttk.Button(
                    self.rcards_frame,
                    text=video_text.format(**{
                        'title': title,
                        'view': d['view'],
                        'comment': d['comment'],
                        'like': d['like'],
                        'post': d['post']
                    }),
                    padding=[0, 0, 0], width=630,
                    style='Ranking.TButton', compound='left',
                    image=thumbnail,
                    command=viewer_click_callback(i)
                )
                card_button.photo = thumbnail
                card_button.pack()
                self.rviewer_canvas.config(scrollregion=(0, 0, 0, (i+1)*49.5))

                # !重要! これがないとプログレスバーが描画されない
                # ループが終わるまで描画の処理が先送りになるため？
                pbar._tk_window.update()
            # 役目を終えたプログレスバーウィンドウを虚空に帰す
            pbar._tk_window.destroy()

    def card_view(self):
        if self.card_button:
            self.card_button.destroy()

        d = self.card_dict
        if len(d['title']) < 90:
            title = d['title']
        else:
            title = d['title'][:90] + '…'

        video_text = '{title}\n▶️{view}💬{comment}💕{like}🕘{post}'
        thumbnail = url2img(d['thumbnail'])
        thumbnail = ImageTk.PhotoImage(thumbnail.resize((102, 77)))

        card_button = ttk.Button(
            self.pane2_frame,
            text=video_text.format(**{
                'title': title,
                'view': d['view'],
                'comment': d['comment'],
                'like': d['like'],
                'post': d['post']
            }),
            style='Card.TButton', compound='left',
            image=thumbnail,
            command=lambda: webbrowser.open(d['url']),
            padding=[0, 0, 0], width=60
        )
        card_button.photo = thumbnail
        card_button.grid(row=0, column=0, sticky=tk.NW)

        self.card_button = card_button

    def comment_view(self):
        notebook = self.tabs_notebook
        tab_frame = notebook.nametowidget(notebook.tabs()[1])

        if self.comment_treeview:
            self.comment_treeview.destroy()

        df = self.comments_df.reset_index().sort_values('write_time')
        df = df.rename(
            columns={
                'comment_id': 'cid', 'user_id': 'uid',
                'write_time': 'wtime', 'video_time': 'vtime'
            }
        ).drop(['184', 'position', 'size', 'color', 'command'], axis=1)
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

        comment_treeview = ttk.Treeview(
            tab_frame,
            columns=list(df.columns), height=35
        )
        for i in range(len(df)):
            values = [df.iloc[i][j] for j in range(len(df.columns))]
            comment_treeview.insert('', 'end', values=values)

        # This code based on https://jablogs.com/detail/13411
        def treeview_sort_column(tv, col, reverse):
            l = [(tv.set(k, col), k) for k in tv.get_children('')]
            l.sort(reverse=reverse)

            # rearrange items in sorted positions
            _ = [tv.move(k, '', index) for index, (val, k) in enumerate(l)]

            # reverse sort next time
            sort_callback = lambda _col=col: treeview_sort_column(
                tv, _col, not reverse
            )
            tv.heading(col, text=col, command=sort_callback)

        comment_treeview['show'] = 'headings'
        _ = [
            (
                comment_treeview.heading(i, text=c, command= \
                    lambda col=c: treeview_sort_column(comment_treeview, col, False)),
                comment_treeview.column(c, width=df_width[c], stretch=False)
            )
            for i, c in enumerate(df.columns)
        ]

        comment_treeview.grid(row=2, column=0)

        self.comment_treeview = comment_treeview

    def wordcloud_view(self):
        notebook = self.tabs_notebook
        tab_frame = notebook.nametowidget(notebook.tabs()[2])

        wordcloud_canvas = tk.Canvas(
            tab_frame,
            width=WORDCLOUD_W,
            height=WORDCLOUD_H
            #relief=tk.RIDGE  # 枠線を表示
            # 枠線の幅を設定
        )

        wordcloud = Image.open('./wordcloud.png')
        wordcloud = ImageTk.PhotoImage(wordcloud)
        wordcloud_canvas.create_image(0, 0, image=wordcloud, anchor=tk.NW)
        wordcloud_canvas.photo = wordcloud
        wordcloud_canvas.grid(row=0, column=0)

        self.wordcloud_canvas = wordcloud_canvas

    def comment_load(self, **options):
        ninfo = NicovideoInfomation(video_url=self.card_dict['url'])
        ninfo.load_comments(**options)
        comments_df = ninfo.comments_df

        self.comments_df = comments_df
        self.org_df = comments_df.copy()

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
