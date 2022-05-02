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
        # tabs
        tabs_notebook = ttk.Notebook(pane2_frame)

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

        self.pane1_frame = pane1_frame
        self.pane2_frame = pane2_frame

        self.tabs_notebook = tabs_notebook

        self.rv_buttons = None
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
        vid_entry = ttk.Entry(panel_frame, textvariable=vid_var, width=35)

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
        vurl_entry = ttk.Entry(panel_frame, textvariable=vurl_var, width=35)

        def vurl_click_callback():
            url = vurl.get()
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

        size_y = 100 * 50
        viewer_canvas.yview_moveto(0)
        viewer_canvas['yscrollcommand'] = viewer_scrollbar.set
        viewer_canvas.config(scrollregion=(0, 0, 0, size_y))

        vcwin_frame = tk.Frame(viewer_canvas)

        viewer_canvas.create_window(
            (0, 0),
            window=vcwin_frame,
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
        self.vcwin_frame = vcwin_frame


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

        # --- load ---
        load_frame = ttk.LabelFrame(
            tab_frame,
            text='コメント読み込み', relief=tk.RIDGE,
            padding=[10, 10, 10, 10]
        )
        lopt_frame = ttk.LabelFrame(
            load_frame, text='options', relief=tk.RIDGE,
            padding=[10, 10, 10, 10]
        )

        lforks_frame = ttk.LabelFrame(
            lopt_frame,
            text='コメントの種類', labelanchor=tk.NW,
            padding=[5, 5, 5, 5]
        )
        lfork0_var = tk.BooleanVar(); lfork0_var.set(True)
        lfork0_checkbutton = ttk.Checkbutton(
            lforks_frame, variable=lfork0_var, text='一般コメント'
        )
        lfork1_var = tk.BooleanVar(); lfork1_var.set(True)
        lfork1_checkbutton = ttk.Checkbutton(
            lforks_frame, variable=lfork1_var, text='投稿者コメント'
        )
        lfork2_var = tk.BooleanVar(); lfork2_var.set(True)
        lfork2_checkbutton = ttk.Checkbutton(
            lforks_frame, variable=lfork2_var, text='かんたんコメント'
        )

        lmode_frame = ttk.LabelFrame(
            lopt_frame, text='mode', labelanchor=tk.NW,
            padding=[5, 5, 5, 5]
        )
        lmode_var = tk.StringVar(value='once')
        once_radiobutton = ttk.Radiobutton(
            lmode_frame, text='once', value='once', variable=lmode_var
        )
        roughly_radiobutton = ttk.Radiobutton(
            lmode_frame, text='roughly', value='roughly', variable=lmode_var
        )
        exactly_radiobutton = ttk.Radiobutton(
            lmode_frame, text='exactly', value='exactly', variable=lmode_var
        )

        hoprate_frame = ttk.LabelFrame(
            lopt_frame, text='hop rate', labelanchor=tk.NW,
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

        def lload_click_callback():
            lforks = [lfork0_var, lfork1_var, lfork2_var]
            options = {
                'forks': [i for i, fork in enumerate(lforks) if fork.get()],
                'mode': lmode_var.get(),
                'hop_rate': hoprate_val.get()
            }

            self.comment_load(**options)
            self.comment_view()
            self.wordcloud_generate()
            self.wordcloud_view()

        lbuttons_frame = ttk.Frame(load_frame, padding=[10, 10, 10, 10])

        lload_button = ttk.Button(
            lbuttons_frame,
            text='load', command=lload_click_callback,
            padding=[0, 0, 0], width=20,

        )

        load_frame.grid(row=0, column=0, padx=10, pady=10)

        lopt_frame.grid(row=0, column=0, padx=10, pady=10)

        lforks_frame.grid(row=0, column=0)
        lfork0_checkbutton.grid(row=0, column=0)
        lfork1_checkbutton.grid(row=0, column=1)
        lfork2_checkbutton.grid(row=0, column=2)

        lmode_frame.grid(row=1, column=0, sticky=tk.W)
        once_radiobutton.grid(row=0, column=0)
        roughly_radiobutton.grid(row=0, column=1)
        exactly_radiobutton.grid(row=0, column=2)

        hoprate_frame.grid(row=2, column=0, sticky=tk.W)
        hoprate_scale.grid(row=0, column=0)
        hoprate_label.grid(row=0, column=1)

        lbuttons_frame.grid(row=0, column=1, padx=10, pady=10)
        lload_button.grid(row=0, column=0)

        # --- extract ---
        extract_frame = ttk.LabelFrame(
            tab_frame,
            text='コメント抽出', relief=tk.RIDGE, padding=[10, 10, 10, 10]
        )
        eopt_frame = ttk.LabelFrame(
            extract_frame, text='options', relief=tk.RIDGE,
            padding=[10, 10, 10, 10]
        )
        eforks_frame = ttk.LabelFrame(
            eopt_frame, text='コメントの種類', labelanchor=tk.NW,
            padding=[5, 5, 5, 5]
        )
        efork0_var = tk.BooleanVar(); efork0_var.set(True)
        efork0_checkbutton = ttk.Checkbutton(
            eforks_frame, variable=efork0_var, text='一般コメント'
        )
        efork1_var = tk.BooleanVar(); efork1_var.set(True)
        efork1_checkbutton = ttk.Checkbutton(
            eforks_frame, variable=efork1_var, text='投稿者コメント'
        )
        efork2_var = tk.BooleanVar(); efork2_var.set(True)
        efork2_checkbutton = ttk.Checkbutton(
            eforks_frame, variable=efork2_var, text='かんたんコメント'
        )

        extract_frame.grid(row=1, column=0, padx=10, pady=10)

        eopt_frame.grid(row=0, column=0)

        eforks_frame.grid(row=0, column=0)
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

        def viewer_click_callback(i):
            def x():
                self.card_dict = self.ranking_info[(i, )[0]]
                _ = self.card_view()
            return x

        video_text = '{title}\n▶️{view}💬{comment}💕{like}🕘{post}'
        rviewer_buttons = []
        with tqdm_tk(info_dict.items()) as pbar:
            for i, d in pbar:
                thumbnail = url2img(d['thumbnail'])
                thumbnail = ImageTk.PhotoImage(thumbnail.resize((63, 47)))
                if len(d['title']) < 50:
                    title = d['title']
                else:
                    title = d['title'][:50] + '…'

                callback = lambda: viewer_click_callback(i)
                card_button = ttk.Button(
                    self.vcwin_frame,
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
                    command=callback()
                )
                card_button.photo = thumbnail
                card_button.pack()
                rviewer_buttons.append(card_button)

                # !重要! これがないとプログレスバーが描画されない
                # ループが終わるまで描画の処理が先送りになるため？
                pbar._tk_window.update()
            # 役目を終えたプログレスバーウィンドウを虚空に帰す
            pbar._tk_window.destroy()

        self.rv_buttons = rviewer_buttons

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
        thumbnail = ImageTk.PhotoImage(thumbnail.resize((93, 70)))

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
