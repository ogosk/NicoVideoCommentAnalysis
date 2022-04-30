import tkinter as tk
from tkinter import ttk
import ttkthemes
from PIL import Image, ImageTk
from wordcloud import WordCloud

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
        
        self.p1_frame = pane1_frame
        self.p2_frame = pane2_frame
        self.c_button = None
        self.rv_buttons = None
        
        self.pane1_set()
        self.pane2_set()
        
    def pane1_set(self):
        self.input_panel_set()
        self.ranking_panel_set()
    
    def pane2_set(self):
        self.card_view()
        self.comment_load_panel_set()
    
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
            text='OK',
            width=3,
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
    
    def comment_load_panel_set(self):
        comment_load_frame = ttk.Frame(self.p2_frame)
        fork0 = tk.BooleanVar(); fork0.set(True)
        fork0_checkbutton = ttk.Checkbutton(
            comment_load_frame, variable=fork0, text='一般コメント'
        )
        fork1 = tk.BooleanVar(); fork1.set(True)
        fork1_checkbutton = ttk.Checkbutton(
            comment_load_frame, variable=fork1, text='投稿者コメント'
        )
        fork2 = tk.BooleanVar(); fork2.set(True)
        fork2_checkbutton = ttk.Checkbutton(
            comment_load_frame, variable=fork2, text='かんたんコメント'
        )
        
        def cl_click_callback():
            self.comment_load()
            self.comment_view()
            self.wordcloud_generate()
            self.wordcloud_view()
        
        comment_load_button = ttk.Button(
            comment_load_frame,
            text='Load', padding=[0, 0, 0], width=4,
            command=cl_click_callback
        )
        
        fork0_checkbutton.grid(row=0, column=0)
        fork1_checkbutton.grid(row=0, column=1)
        fork2_checkbutton.grid(row=0, column=2)
        comment_load_button.grid(row=0, column=3)#, sticky='nsw')
        
        comment_load_frame.grid(row=1, column=0)
        
        self.forks = [fork0, fork1, fork2]

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
        for i, d in info_dict.items():
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
            image=thumbnail
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
        tree = ttk.Treeview(
            self.p2_frame,
            columns=list(df.columns), height=20
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
        wordcloud_canvas = tk.Canvas(
            self.p2_frame,
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
        wordcloud_canvas.grid(row=3, column=0)
    
    def comment_load(self):
        ninfo = NicovideoInfomation(video_url=self.card_dict['url'])
        forks = [i for i, fork in enumerate(self.forks) if fork.get()]
        # ninfo.load_comments(forks, hop_rate=.2, mode='exactly', check=False)
        ninfo.load_comments(forks, mode='once', check=False)
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
    main()#sm40400302