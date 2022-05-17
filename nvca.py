import tkinter as tk
from tkinter import ttk, filedialog
# import tkcalendar as tkc
import ttkthemes
import numpy as np
import pandas as pd
import webbrowser
import datetime
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

COMMENT_LINES = 35

WORDCLOUD_W = 600
WORDCLOUD_H = 450


class Application(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)

        self.master.title("NicoVideoCommentAnalysis")

        # pane1
        pane1_frame = ttk.Frame(self.master)
        # pane2
        pane2_frame = ttk.Frame(self.master)
        # tabs
        tabs_notebook = ttk.Notebook(pane2_frame)

        pane1_frame.pack(side=tk.LEFT, anchor=tk.N)
        pane2_frame.pack(side=tk.LEFT, anchor=tk.N, fill=tk.Y)

        # style
        style = ttk.Style()
        style.theme_use('black')
        style.configure(
            'Ranking.TButton',
            anchor=tk.W, borderwidth=0, justify=tk.LEFT, wraplength=350
        )
        style.configure(
            'Card.TButton',
            anchor=tk.W, borderwidth=0, justify=tk.LEFT, wraplength=580
        )
        style.configure(
            'Normal.TButton',
            anchor=tk.CENTER
        )
        style.map('White.TCheckbutton',   foreground=[('!disabled', '#FFFFFF'), ('disabled', '#333333')])
        style.map('Red.TCheckbutton',     foreground=[('!disabled', '#FF0000'), ('disabled', '#333333')])
        style.map('Pink.TCheckbutton',    foreground=[('!disabled', '#FF8080'), ('disabled', '#333333')])
        style.map('Orange.TCheckbutton',  foreground=[('!disabled', '#FFC000'), ('disabled', '#333333')])
        style.map('Yellow.TCheckbutton',  foreground=[('!disabled', '#FFFF00'), ('disabled', '#333333')])
        style.map('Green.TCheckbutton',   foreground=[('!disabled', '#00FF00'), ('disabled', '#333333')])
        style.map('Cyan.TCheckbutton',    foreground=[('!disabled', '#00FFFF'), ('disabled', '#333333')])
        style.map('Blue.TCheckbutton',    foreground=[('!disabled', '#0000FF'), ('disabled', '#333333')])
        style.map('Purple.TCheckbutton',  foreground=[('!disabled', '#C000FF'), ('disabled', '#333333')])
        style.map('Black.TCheckbutton',   foreground=[('!disabled', '#000000'), ('disabled', '#333333')])
        style.map('White2.TCheckbutton',  foreground=[('!disabled', '#CCCC99'), ('disabled', '#333333')])
        style.map('Red2.TCheckbutton',    foreground=[('!disabled', '#CC0033'), ('disabled', '#333333')])
        style.map('Pink2.TCheckbutton',   foreground=[('!disabled', '#FF33CC'), ('disabled', '#333333')])
        style.map('Orange2.TCheckbutton', foreground=[('!disabled', '#FF6600'), ('disabled', '#333333')])
        style.map('Yellow2.TCheckbutton', foreground=[('!disabled', '#999900'), ('disabled', '#333333')])
        style.map('Green2.TCheckbutton',  foreground=[('!disabled', '#00CC66'), ('disabled', '#333333')])
        style.map('Cyan2.TCheckbutton',   foreground=[('!disabled', '#00CCCC'), ('disabled', '#333333')])
        style.map('Blue2.TCheckbutton',   foreground=[('!disabled', '#3399FF'), ('disabled', '#333333')])
        style.map('Purple2.TCheckbutton', foreground=[('!disabled', '#6633CC'), ('disabled', '#333333')])
        style.map('Black2.TCheckbutton',  foreground=[('!disabled', '#666666'), ('disabled', '#333333')])
        style.configure('Comment.Treeview', rowheight=20)

        style.configure('Debug.TFrame', background='#FFFFFF')

        # insrtance var
        # dummy
        self.card_dict = {
            'url': '',
            'title': '',
            'owner': '',
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

        self.pane1_set()
        self.pane2_set()

    def pane1_set(self):
        self.input_panel_set()
        self.ranking_panel_set()

    def pane2_set(self):
        self.tabs_set()
        self.control_tab_set()
        self.comment_tab_set()
        self.wordcloud_tab_set()

        self.card_view()

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
            style='Normal.TButton', width=5
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
            panel_frame, style='Normal.TButton',
            text='OK',
            command=vurl_click_callback,
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
            panel_frame, state='readonly', textvariable=genre_var,
            values=list(genres_dict.keys()),
            width=15
        )

        genres_combobox.current(0)

        # === term ===
        term_var = tk.StringVar()
        terms_combobox = ttk.Combobox(
            panel_frame, state='readonly', textvariable=term_var,
            values=list(terms_dict.keys()),
            width=5
        )

        terms_combobox.current(0)

        select_button = ttk.Button(
            panel_frame, style='Normal.TButton',
            text='ランキング取得',
            command=self.ranking_view,
            width=10
        )

        # === ranking viewer ===
        viewer_frame = ttk.Frame(panel_frame)
        viewer_canvas = tk.Canvas(
            viewer_frame,
            width=420, height=755#int(845/42*(COMMENT_LINES+2))# 30->750 40->845
        )
        viewer_scrollbar = ttk.Scrollbar(
            viewer_frame,
            command=viewer_canvas.yview,
            orient=tk.VERTICAL,
        )

        viewer_canvas.yview_moveto(0)
        viewer_canvas.config(
            yscrollcommand=viewer_scrollbar.set,
            scrollregion=(0, 0, 0, 0)
        )

        # this code is from https://jablogs.com/detail/2137
        def bound_to_mousewheel(event):
            viewer_canvas.bind_all('<MouseWheel>', on_mousewheel)

        def unbound_to_mousewheel(event):
            viewer_canvas.unbind_all('<MouseWheel>')

        def on_mousewheel(event):
            # Windows
            # viewer_canvas.yview_scroll(-1*int(event.delta/120), 'units')
            # OSX
            viewer_canvas.yview_scroll(-1*int(event.delta), 'units')

        viewer_frame.bind('<Enter>', bound_to_mousewheel)
        viewer_frame.bind('<Leave>', unbound_to_mousewheel)

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
        self.tabs_notebook.add(comment_tab, text='コメント', state='disabled')
        self.tabs_notebook.add(wordcloud_tab, text='WordCloud', state='disabled')

        self.tabs_notebook.grid(row=1, column=0)

        self.tabs_dict = {
            'control': 0, 'comment': 1, 'wordcloud': 2
        }

    def control_tab_set(self):
        notebook, tabs_dict = self.tabs_notebook, self.tabs_dict
        tab_frame = notebook.nametowidget(notebook.tabs()[tabs_dict['control']])

        # === load ===
        def load_set():
            load_frame = ttk.LabelFrame(
                tab_frame,
                text='コメント読み込み',
                relief=tk.RIDGE, padding=[10, 10, 10, 10]
            )
            opt_frame = ttk.LabelFrame(
                load_frame,
                text='options',
                relief=tk.RIDGE, padding=[10, 10, 10, 10]
            )

            forks_frame = ttk.LabelFrame(
                opt_frame,
                text='コメントの種類',
                labelanchor=tk.NW, padding=[5, 5, 5, 5]
            )
            fork0_var = tk.BooleanVar(value=True)
            fork0_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork0_var,
                text='一般コメント'
            )
            fork1_var = tk.BooleanVar(value=True)
            fork1_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork1_var,
                text='投稿者コメント'
            )
            fork2_var = tk.BooleanVar(value=True)
            fork2_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork2_var,
                text='かんたんコメント'
            )

            # span_frame = ttk.LabelFrame(
            #     opt_frame,
            #     text='取得期間',
            #     labelanchor=tk.NW, padding=[5, 5, 5, 5]
            # )

            # start_dateentry = tkc.DateEntry(
            #     span_frame, lacale='jp_JP', mindate=
            # )
            # end_dateentry = tkc.DateEntry(
            #     span_frame, lacale='jp_JP'
            # )
            #
            # calendar_dateentry.pack(anchor=tk.W)

            mode_frame = ttk.LabelFrame(
                opt_frame,
                text='mode',
                labelanchor=tk.NW, padding=[5, 5, 5, 5]
            )
            mode_var = tk.StringVar(value='once')
            once_radiobutton = ttk.Radiobutton(
                mode_frame, variable=mode_var,
                text='once', value='once'
            )
            roughly_radiobutton = ttk.Radiobutton(
                mode_frame, variable=mode_var,
                text='roughly', value='roughly'
            )
            exactly_radiobutton = ttk.Radiobutton(
                mode_frame, variable=mode_var,
                text='exactly', value='exactly'
            )

            def check_echeckbuttons():
                df = self.comments_df
                ebuttons_dict = self.echeckbuttons_dict

                for b_type, bs_dict in ebuttons_dict.items():
                    for b_name, b_dict in bs_dict.items():
                        var, button = b_dict['var'], b_dict['checkbutton']

                        if b_type == 'forks':
                            vals = df.index.str[0]
                        else:
                            vals = df[b_type].values

                        if b_name not in vals:
                            var.set(False)
                            button['state'] = 'disable'
                        else:
                            var.set(True)
                            button['state'] = 'enable'

            def check_overview(overview):
                df, org_df = self.comments_df, self.org_df
                forks = sorted(list(set(df.index.str[0])))
                overview.delete(*overview.get_children())

                c_dict = {'0': '一般コメント', '1': '投稿者コメント', '2': 'かんたんコメント'}
                c_nums, rows = [], []
                for fork in forks:
                    got = df[df.index.str[0]==fork]
                    org = org_df[org_df.index.str[0]==fork]
                    c_indices = list(map(int, org.index.str[2:]))
                    c_got_num = len(got)
                    c_nums.append(max(c_indices))
                    u_got_num = len(set(got.user_id))

                    rows.append(
                        overview.insert(
                            '', tk.END, text=c_dict[fork], open=False
                        )
                    )
                    _ = overview.insert(
                        rows[-1], tk.END, text='コメント数', value=c_got_num
                    )
                    _ = overview.insert(
                        rows[-1], tk.END, text='ユーザー数', value=u_got_num
                    )
                    _ = overview.insert(
                        rows[-1], tk.END, text='推定取得率', value=f'{c_got_num/c_nums[-1]:.2%}'
                    )

                c_got_num, c_num = len(df), sum(c_nums)
                u_got_num = len(set(df.user_id))
                if len(forks) > 1:
                    row = overview.insert(
                        '', 0, text='トータル', open=True
                    )
                    _ = overview.insert(
                        row, tk.END, text='コメント数', value=c_got_num
                    )
                    _ = overview.insert(
                        row, tk.END, text='ユーザー数', value=u_got_num
                    )
                    _ = overview.insert(
                        row, tk.END, text='推定取得率', value=f'{c_got_num/c_num:.2%}'
                    )
                else:
                    overview.item(rows[0], open=True)

            def load_click_callback():
                forks = [fork0_var, fork1_var, fork2_var]
                options = {
                    'forks': [i for i, fork in enumerate(forks) if fork.get()],
                    'mode': mode_var.get(),
                    'check': False,
                    'tqdm_fn': tqdm_tk
                }
                self.tabs_notebook.tab(tab_id=tabs_dict['comment'], state='normal')
                self.tabs_notebook.tab(tab_id=tabs_dict['wordcloud'], state='normal')

                self.comment_load(**options)
                self.comment_view()
                check_echeckbuttons()
                check_overview(overview_treeview)

                for button in self.ebuttons_frame.winfo_children():
                    button['state'] = 'enable'

                save_button['state'] = 'enable'

            def save_click_callback():
                timestamp = datetime.datetime.today().strftime('%y%m%d%H')
                vid = self.ninfo.video_id
                filename = filedialog.asksaveasfilename(
                    parent=self.master,
                    title='save',
                    initialfile=f'{timestamp}_{vid}',
                    filetypes=[('csv', '.csv'), ('pickle', '.pkl')],
                    initialdir = "./",
                    defaultextension='csv'
                )
                extension = filename.split('.')[-1]
                if extension == 'csv':
                    self.org_df.to_csv(filename)
                elif extension == 'pkl':
                    self.org_df.to_pickle(filename)

            buttons_frame = ttk.Frame(load_frame, padding=[10, 10, 10, 10])

            load_button = ttk.Button(
                buttons_frame, style='Normal.TButton',
                text='load',
                command=load_click_callback,
                width=8, padding=[0, 5, 0],
            )
            save_button = ttk.Button(
                buttons_frame, style='Normal.TButton', state='disable',
                text='save',
                command=save_click_callback,
                width=8, padding=[0, 5, 0]
            )

            abstract_frame = ttk.LabelFrame(
                load_frame,
                text='取得コメント概要',
                relief=tk.RIDGE, padding=[10, 10, 10, 10]
            )

            cols = ['#0', 'data']
            params = {
                '#0':   {'text': '種類', 'width': 180},
                'data': {'text': 'データ', 'width': 140}
            }
            overview_treeview = ttk.Treeview(
                abstract_frame, columns=cols[1:], height=5
            )
            _ = [
                (
                    overview_treeview.column(col, width=params[col]['width']),
                    overview_treeview.heading(col, text=params[col]['text'])
                )
                for col in cols
            ]

            overview_treeview['height'] = 6

            load_frame.pack(anchor=tk.NW, fill=tk.X, padx=10, pady=10)

            opt_frame.pack(side=tk.LEFT, anchor=tk.W, fill=tk.Y, expand=True)

            forks_frame.pack(anchor=tk.W, fill=tk.X, expand=True)
            fork0_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            fork1_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            fork2_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)

            mode_frame.pack(anchor=tk.W, fill=tk.X, expand=True)
            once_radiobutton.pack(side=tk.LEFT, padx=[0, 20])
            roughly_radiobutton.pack(side=tk.LEFT, padx=20)
            exactly_radiobutton.pack(side=tk.LEFT, padx=20)

            buttons_frame.pack(anchor=tk.NW, expand=True, fill=tk.X, pady=10)
            load_button.pack(side=tk.LEFT, anchor=tk.CENTER, expand=True)
            save_button.pack(side=tk.LEFT, anchor=tk.CENTER, expand=True)

            abstract_frame.pack(anchor=tk.SW, fill=tk.Y, expand=True)
            overview_treeview.pack(expand=True)

        load_set()

        # === extract ===
        def extract_set():
            extract_frame = ttk.LabelFrame(
                tab_frame,
                text='コメント抽出',
                relief=tk.RIDGE, padding=[10, 10, 10, 10]
            )

            opt1_frame = ttk.LabelFrame(
                extract_frame,
                text='options',
                relief=tk.RIDGE, padding=[10, 10, 10, 10]
            )
            opt2_frame = ttk.Frame(
                extract_frame,
                relief=tk.RIDGE, padding=[10, 10, 10, 10]
            )

            forks_frame = ttk.LabelFrame(
                opt1_frame,
                text='コメントの種類',
                labelanchor=tk.NW, padding=[5, 5, 5, 5]
            )
            fork0_var = tk.BooleanVar(value=True)
            fork0_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork0_var,
                text='一般コメント'
            )
            fork1_var = tk.BooleanVar(value=True)
            fork1_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork1_var,
                text='投稿者コメント'
            )
            fork2_var = tk.BooleanVar(value=True)
            fork2_checkbutton = ttk.Checkbutton(
                forks_frame, variable=fork2_var,
                text='かんたんコメント'
            )
            forks_dict = {
                '0': {'var': fork0_var, 'checkbutton': fork0_checkbutton},
                '1': {'var': fork1_var, 'checkbutton': fork1_checkbutton},
                '2': {'var': fork2_var, 'checkbutton': fork2_checkbutton}
            }

            comment_frame = ttk.LabelFrame(
                opt1_frame,
                text='コメント (スペース区切りでAND検索可)',
                labelanchor=tk.NW, padding=[5, 5, 5, 5]
            )
            comment_var = tk.StringVar()
            comment_entry = tk.Entry(comment_frame, textvariable=comment_var)

            uid_frame = ttk.LabelFrame(
                opt1_frame,
                text='ユーザーID (スペース区切りでOR検索可)',
                labelanchor=tk.NW, padding=[5, 5, 5, 5]
            )
            uid_var = tk.StringVar()
            uid_entry = tk.Entry(uid_frame, textvariable=uid_var)

            position_frame = ttk.LabelFrame(
                opt1_frame,
                text='コメントの位置 (デフォルト：中)',
                labelanchor=tk.NW, padding=[5, 5, 5, 5]
            )
            positions = ['ue', 'naka', 'shita']
            positions_dict = {
                p: {
                    'var': var,
                    'checkbutton': ttk.Checkbutton(
                        position_frame,
                        variable=var,
                        text={'ue': '上', 'naka': '中', 'shita': '下'}[p],
                    )
                } for p, var in [(p, tk.BooleanVar(value=True)) for p in positions]
            }

            size_frame = ttk.LabelFrame(
                opt2_frame,
                text='コメントの大きさ (デフォルト：中)',
                labelanchor=tk.NW, padding=[5, 5, 5, 5]
            )
            sizes = ['big', 'medium', 'small']
            sizes_dict = {
                s: {
                    'var': var,
                    'checkbutton': ttk.Checkbutton(
                        size_frame,
                        variable=var,
                        text={'big': '大', 'medium': '中', 'small': '小'}[s],
                    )
                } for s, var in [(s, tk.BooleanVar(value=True)) for s in sizes]
            }

            color_frame = ttk.LabelFrame(
                opt1_frame,
                text='コメントの色',
                labelanchor=tk.NW, padding=[5, 5, 5, 5]
            )
            general_frame = ttk.LabelFrame(
                color_frame,
                text='全ユーザー',
                labelanchor=tk.NW
            )
            premium_frame = ttk.LabelFrame(
                color_frame,
                text='プレミアム会員限定',
                labelanchor=tk.NW
            )
            gcolors = [
                'white', 'red', 'pink', 'orange', 'yellow', 'green',
                'cyan', 'blue', 'purple', 'black'
            ]
            pcolors = [c+'2' for c in gcolors]
            colors = gcolors + pcolors
            colors_dict = {
                c: {
                    'var': var,
                    'checkbutton': ttk.Checkbutton(
                        general_frame if c in gcolors else premium_frame,
                        variable=var,
                        text='●',
                        style=f'{c[0].upper()+c[1:]}.TCheckbutton'
                    )
                } for c, var in [(c, tk.BooleanVar(value=True)) for c in colors]
            }

            def make_opt_dict():
                forks = [fork0_var, fork1_var, fork2_var]
                opt_dict = {
                    'forks': [str(i) for i, fork in enumerate(forks) if fork.get()],
                    'comment': comment_var.get(),
                    'user_id': uid_var.get(),
                    'write_time': (None, None),
                    'video_time': (None, None),
                    'position': [p for p, v in positions_dict.items() if v['var'].get()],
                    'size': [s for s, v in sizes_dict.items() if v['var'].get()],
                    'color': [c for c, v in colors_dict.items() if v['var'].get()],
                    'score': (None, None)
                }
                return opt_dict

            def check_overview(overview):
                df, org_df = self.comments_df, self.org_df
                forks = sorted(list(set(df.index.str[0])))
                overview.delete(*overview.get_children())

                c_dict = {'0': '一般コメント', '1': '投稿者コメント', '2': 'かんたんコメント'}
                c_nums, rows = [], []
                for fork in forks:
                    got = df[df.index.str[0]==fork]
                    org = org_df[org_df.index.str[0]==fork]
                    c_indices = list(map(int, org.index.str[2:]))
                    c_got_num = len(got)
                    c_nums.append(len(c_indices))
                    u_got_num = len(set(got.user_id))

                    rows.append(
                        overview.insert(
                            '', tk.END, text=c_dict[fork], open=False
                        )
                    )
                    _ = overview.insert(
                        rows[-1], tk.END, text='コメント数', value=c_got_num
                    )
                    _ = overview.insert(
                        rows[-1], tk.END, text='ユーザー数', value=u_got_num
                    )
                    _ = overview.insert(
                        rows[-1], tk.END, text='抽出率', value=f'{c_got_num/c_nums[-1]:.2%}'
                    )

                c_got_num, c_num = len(df), sum(c_nums)
                u_got_num = len(set(df.user_id))
                if len(forks) > 1:
                    row = overview.insert(
                        '', 0, text='トータル', open=True
                    )
                    _ = overview.insert(
                        row, tk.END, text='コメント数', value=c_got_num
                    )
                    _ = overview.insert(
                        row, tk.END, text='ユーザー数', value=u_got_num
                    )
                    _ = overview.insert(
                        row, tk.END, text='抽出率', value=f'{c_got_num/c_num:.2%}'
                    )
                else:
                    overview.item(rows[0], open=True)

            def select_click_callback():
                opt_dict = make_opt_dict()
                df = self.org_df

                if opt_dict['comment']:
                    df = df[
                        np.all(
                            [
                                df.comment.str.contains(com)
                                for com in opt_dict['comment'].split(' ')
                            ],
                            axis=0
                        )
                    ]

                if opt_dict['user_id']:
                    df = df[df.user_id.isin(opt_dict['user_id'].split(' '))]

                df = df[np.all(
                    (
                        df.index.str[0].isin(opt_dict['forks']),
                        df.position.isin(opt_dict['position']),
                        df['size'].isin(opt_dict['size']),
                        df.color.isin(opt_dict['color'])
                    ),
                    axis=0
                )].sort_values('write_time')

                self.comments_df = df

                check_overview(overview_treeview)
                self.comment_view()

            def reset_click_callback():
                for elems_dict in self.echeckbuttons_dict.values():
                    for elems in elems_dict.values():
                        var, button = elems['var'], elems['checkbutton']
                        if button['state'] == 'enable':
                            var.set(True)

                for elems_dict in self.eentries_dict.values():
                    for elems in elems_dict.values():
                        var, entry = elems_dict['var'], elems_dict['entry']
                        var.set('')

            def save_click_callback():
                timestamp = datetime.datetime.today().strftime('%y%m%d%H')
                vid = self.ninfo.video_id
                filename = filedialog.asksaveasfilename(
                    parent=self.master,
                    title='save',
                    initialfile=f'{timestamp}_{vid}',
                    filetypes=[('csv', '.csv'), ('pickle', '.pkl')],
                    initialdir = "./",
                    defaultextension='csv'
                )
                extension = filename.split('.')[-1]
                if extension == 'csv':
                    self.comments_df.to_csv(filename)
                elif extension == 'pkl':
                    self.comments_df.to_pickle(filename)

            buttons_frame = ttk.Frame(extract_frame, padding=[10, 10, 10, 10])

            select_button = ttk.Button(
                buttons_frame, style='Normal.TButton', state='disable',
                text='select',
                command=select_click_callback,
                width=8, padding=[0, 5, 0]
            )
            reset_button = ttk.Button(
                buttons_frame, style='Normal.TButton', state='disable',
                text='reset',
                command=reset_click_callback,
                width=8, padding=[0, 5, 0]
            )
            save_button = ttk.Button(
                buttons_frame, style='Normal.TButton', state='disable',
                text='save',
                command=save_click_callback,
                width=8, padding=[0, 5, 0]
            )

            abstract_frame = ttk.LabelFrame(
                extract_frame,
                text='抽出コメント概要',
                relief=tk.RIDGE, padding=[10, 10, 10, 10]
            )

            cols = ['#0', 'data']
            params = {
                '#0':   {'text': '種類', 'width': 180},
                'data': {'text': 'データ', 'width': 140}
            }
            overview_treeview = ttk.Treeview(
                abstract_frame, columns=cols[1:], height=5
            )
            _ = [
                (
                    overview_treeview.column(col, width=params[col]['width']),
                    overview_treeview.heading(col, text=params[col]['text'])
                )
                for col in cols
            ]

            overview_treeview['height'] = 6

            extract_frame.pack(anchor=tk.NW, fill=tk.X, padx=10, pady=10)

            opt1_frame.pack(side=tk.LEFT, expand=True, anchor=tk.NW)
            opt2_frame.pack(anchor=tk.NW, expand=True, fill=tk.X, pady=[8, 0])

            forks_frame.pack(anchor=tk.W, expand=True)
            fork0_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            fork1_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)
            fork2_checkbutton.pack(side=tk.LEFT, fill=tk.X, expand=True)

            comment_frame.pack(anchor=tk.W, expand=True)
            comment_entry.pack(side=tk.LEFT)

            uid_frame.pack(anchor=tk.W, expand=True)
            uid_entry.pack(side=tk.LEFT)

            color_frame.pack(anchor=tk.W, expand=True)
            general_frame.pack(fill=tk.X, expand=True)
            premium_frame.pack(fill=tk.X, expand=True)
            _ = [
                colors_dict[c]['checkbutton'].pack(side=tk.LEFT, fill=tk.X, expand=True)
                for c in colors
            ]

            position_frame.pack(anchor=tk.W, expand=True)
            _ = [
                positions_dict[p]['checkbutton'].pack(side=tk.LEFT, padx=[0, 30])
                if p == 'ue'
                else positions_dict[p]['checkbutton'].pack(side=tk.LEFT, padx=30)
                for p in positions
            ]

            size_frame.pack(anchor=tk.W, expand=True)
            _ = [
                sizes_dict[s]['checkbutton'].pack(side=tk.LEFT, padx=[0, 30])
                if s == 'big'
                else sizes_dict[s]['checkbutton'].pack(side=tk.LEFT, padx=30)
                for s in sizes
            ]

            buttons_frame.pack(anchor=tk.W, fill=tk.X, expand=True)
            select_button.pack(side=tk.LEFT, anchor=tk.CENTER, expand=True)
            reset_button.pack(side=tk.LEFT, anchor=tk.CENTER, expand=True)
            save_button.pack(side=tk.LEFT, anchor=tk.CENTER, expand=True)

            abstract_frame.pack(anchor=tk.SW, fill=tk.BOTH, expand=True)
            overview_treeview.pack()

            self.echeckbuttons_dict = {
                'forks': forks_dict,
                'position': positions_dict,
                'size': sizes_dict,
                'color': colors_dict
            }
            self.eentries_dict = {
                'comment': {'var': comment_var, 'entry': comment_entry},
                'uid': {'var': uid_var, 'entry': uid_entry}
            }
            self.ebuttons_frame = buttons_frame

        extract_set()

    def wordcloud_tab_set(self):
        notebook, tabs_dict = self.tabs_notebook, self.tabs_dict
        tab_frame = notebook.nametowidget(notebook.tabs()[tabs_dict['wordcloud']])

        def plot_click_callback():
            self.wordcloud_generate()
            self.wordcloud_view()
            save_button['state'] = 'enable'

        def save_click_callback():
            timestamp = datetime.datetime.today().strftime('%y%m%d%H')
            vid = self.ninfo.video_id
            filename = filedialog.asksaveasfilename(
                parent=self.master,
                title='save',
                initialfile=f'{timestamp}_{vid}',
                filetypes=[('JPEG', '.jpg'), ('PNG', '.png')],
                initialdir = "./",
                defaultextension='png'
            )
            self.wordcloud_img.save(filename)

        note_label = ttk.Label(
            tab_frame,
            text='読み込みや抽出の際に「かんたんコメント」を除去しておくのがおすすめ'
        )

        buttons_frame = ttk.Frame(tab_frame, padding=[10, 10, 10, 10])

        plot_button = ttk.Button(
            buttons_frame,
            text='plot', command=plot_click_callback,
            style='Normal.TButton', padding=[0, 5, 0], width=8
        )
        save_button = ttk.Button(
            buttons_frame,
            text='save', state='disable', command=save_click_callback,
            style='Normal.TButton', padding=[0, 5, 0], width=8
        )

        wordcloud_canvas = tk.Canvas(
            tab_frame,
            width=WORDCLOUD_W,
            height=WORDCLOUD_H
        )

        note_label.pack(anchor=tk.N)

        buttons_frame.pack(anchor=tk.N, fill=tk.X, expand=True)
        plot_button.pack(side=tk.LEFT, anchor=tk.N, expand=True)
        save_button.pack(side=tk.LEFT, anchor=tk.N, expand=True)

        wordcloud_canvas.pack(anchor=tk.N, expand=True)

        self.wordcloud_canvas = wordcloud_canvas

    def comment_tab_set(self):
        notebook, tabs_dict = self.tabs_notebook, self.tabs_dict
        tab_frame = notebook.nametowidget(notebook.tabs()[tabs_dict['comment']])

        params = {
            'comment_id': {'width': 60,  'text': 'ｺﾒﾝﾄID'},
            'comment':    {'width': 400, 'text': 'コメント'},
            'user_id':    {'width': 60,  'text': 'ﾕｰｻﾞｰID'},
            'write_time': {'width': 120, 'text': '書き込み時間'},
            'video_time': {'width': 60,  'text': '再生時間'},
            '184':        {'width': 20,  'text': '184'},
            'position':   {'width': 50,  'text': '位置'},
            'size':       {'width': 50,  'text': '大きさ'},
            'color':      {'width': 50,  'text': '色'},
            'command':    {'width': 50,  'text': 'コマンド'},
            'score':      {'width': 50,  'text': 'スコア'}
        }

        columns = [
            'comment_id', 'comment', 'user_id', 'write_time', 'video_time', 'score'
        ]

        comment_treeview = ttk.Treeview(
            tab_frame, style='Comment.Treeview',
            show='headings', columns=columns,
            height=COMMENT_LINES
        )

        def treeview_sort_callback(tv, col):
            # 2回クリックで昇順と降順に対応する
            df_sample = pd.concat([self.comments_df[:5], self.comments_df[-5:]])
            asc_sample = df_sample.sort_values(
                [col, 'write_time'], ascending=[True, True]
            )
            desc_sample = df_sample.sort_values(
                [col, 'write_time'], ascending=[False, True]
            )

            if (df_sample.index == asc_sample.index).all():
                self.comments_df = self.comments_df.sort_values(
                    [col, 'write_time'], ascending=[False, True]
                )
            else:
                self.comments_df = self.comments_df.sort_values(
                    [col, 'write_time'], ascending=[True, True]
                )

            self.comment_view()

        _ = [
            (
                comment_treeview.heading(
                    col,
                    text=params[col]['text'],
                    command= lambda col_=col: \
                        treeview_sort_callback(comment_treeview, col_)
                ),
                comment_treeview.column(
                    col,
                    width=params[col]['width'],
                    stretch=False
                )
            )
            for col in columns
        ]

        comment_treeview.pack(fill=tk.X)

        self.comment_treeview = comment_treeview

        self.columns = columns

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

        video_text = '{title}\n▶️{view} 💬{comment} 💕{like} 🕘{post}'
        card_width = self.rcards_frame.winfo_width()
        with tqdm_tk(info_dict.items(), leave=False) as pbar:
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
                        'view':    d['view'],
                        'comment': d['comment'],
                        'like':    d['like'],
                        'post':    d['post']
                    }),
                    padding=[0, 0, 0], width=card_width,
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

    def card_view(self):
        if self.card_button:
            self.card_button.destroy()

        card_dict = self.card_dict

        if card_dict['url']:
            self.ninfo = NicovideoInfomation(video_url=card_dict['url'])
        else:
            self.ninfo = None

        if len(card_dict['title']) < 90:
            title = card_dict['title']
        else:
            title = card_dict['title'][:90] + '…'

        video_text = '{title}\n{owner}・▶️{view} 💬{comment} 💕{like} 🕘{post}'
        thumbnail = url2img(card_dict['thumbnail'])
        thumbnail = ImageTk.PhotoImage(thumbnail.resize((102, 77)))

        def card_click_callback():
            from pathlib import Path

            with open('tmp/video.html', mode='w') as f:
                f.write(self.ninfo.video_html())
            webbrowser.open_new('file://'+str(Path('tmp/video.html').resolve()))

            # tkinterweb が HTML5 に未対応なので断念
            # from tkinterweb import HtmlFrame
            # from pathlib import Path
            # video_win = tk.Toplevel(self)
            # video_win.title(d['url'])
            # video_frame = HtmlFrame(video_win)
            # video_frame.load_url('file://'+str(Path('tmp/video.html').resolve()))
            # video_frame.pack(fill='both', expand=True)

        card_button = ttk.Button(
            self.pane2_frame, style='Card.TButton',
            text=video_text.format(**{
                'title':   title,
                'owner':   self.ninfo.owner_name if self.ninfo else '',
                'view':    card_dict['view'],
                'comment': card_dict['comment'],
                'like':    card_dict['like'],
                'post':    card_dict['post']
            }) if card_dict['url'] else '',
            image=thumbnail, compound='left',
            command=card_click_callback if card_dict['url'] else None,
            width=65, padding=[0, 0, 0]
        )

        card_button.photo = thumbnail
        card_button.grid(row=0, sticky=tk.NW+tk.EW)

        self.card_button = card_button

    def comment_view(self):
        if self.comment_treeview:
            comment_treeview = self.comment_treeview
            comment_treeview.delete(*comment_treeview.get_children())

        df = self.comments_df.reset_index().drop(
            [col for col in self.comments_df.columns if col not in self.columns],
            axis=1
        )

        for i in range(len(df)):
            values = [
                datetime.datetime.fromtimestamp(df.iloc[i][col]).strftime('%y/%m/%d %H:%M:%S')
                if col == 'write_time'
                else str(datetime.timedelta(seconds=int(df.iloc[i][col])))
                if col == 'video_time'
                else df.iloc[i][col].replace('\n', '')
                if col == 'comment'
                else df.iloc[i][col]
                for col in self.columns
            ]
            comment_treeview.insert('', tk.END, values=values)

    def wordcloud_view(self):
        wordcloud_canvas = self.wordcloud_canvas

        wordcloud = ImageTk.PhotoImage(self.wordcloud_img)
        wordcloud_canvas.create_image(0, 0, image=wordcloud, anchor=tk.NW)
        wordcloud_canvas.photo = wordcloud

    def comment_load(self, **options):
        self.ninfo.load_comments(**options)

        self.comments_df = self.ninfo.comments_df.copy()
        self.org_df = self.comments_df.copy()

    def wordcloud_generate(self):
        df = self.comments_df
        results = analyze_comments(df.comment, tokenizer='sudachi')
        text = ' '.join(results)

        font_path = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
        wordcloud = WordCloud(
            background_color='white',
            font_path=font_path,
            width=WORDCLOUD_W,
            height=WORDCLOUD_H,
            max_words=500
        ).generate(text)

        self.wordcloud_img = Image.fromarray(wordcloud.to_array())


def main():
    win = ttkthemes.ThemedTk()
    app = Application(master=win)

    win.mainloop()


if __name__ == '__main__':
    main()
