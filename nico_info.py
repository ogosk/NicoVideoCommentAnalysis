import requests
import json
import datetime
import pandas as pd
import numpy as np
from time import sleep

from bs4 import BeautifulSoup
from tqdm.auto import tqdm
from typing import Union, List


base_params = {
    'version': '20090904',
    'scores': '1',
    'language': '0',
    'force_184': '1',
}

# default: dict[key][0]
basic_commands = {
    'position': ['naka', 'ue', 'shita'],
    'size': ['medium', 'small', 'big'],
    'color': [
        'white', 'red', 'pink', 'orange', 'yellow',
        'green', 'cyan', 'blue', 'purple', 'black',
        'white2', 'red2', 'pink2', 'orange2', 'yellow2',
        'green2', 'cyan2', 'blue2', 'purple2', 'black2',
        'niconicowhite', 'truered', 'passionorange', 'madyellow',
        'elementalgreen', 'marineblue',  'nobleviolet'
    ]
}


class NicovideoInfomation():
    def __init__(self, video_url: str = None, video_id: str = None):
        assert any([video_url, video_id])

        if video_id:
            video_url = f'https://www.nicovideo.jp/watch/{video_id}'

        source = requests.get(video_url)

        soup = BeautifulSoup(source.text, 'html.parser')
        js = json.loads(
            soup.select_one('#js-initial-watch-data').get('data-api-data')
        )
        threads = sorted(js['comment']['threads'], key=lambda x: x['fork'])

        if len(threads) > 3:
            threads.pop(0)

        api_url = threads[0]['server'] + '/api.json'

        post_time = datetime.datetime.strptime(
            js['video']['registeredAt'], '%Y-%m-%dT%H:%M:%S+09:00'
        ).timestamp()

        video_id = js['video']['id']
        video_title = js['video']['title']
        video_counter = js['video']['count']
        video_url = video_url[:video_url.index(video_id)+len(video_id)]

        if js['owner']:
            self.owner_id = js['owner']['id']
            self.owner_name = js['owner']['nickname']
        elif js['channel']:
            self.owner_id = js['channel']['id']
            self.owner_name = js['channel']['name']

        self.video_id = video_id
        self.video_title = video_title
        self.video_url = video_url
        self.video_counter = video_counter
        self.post_time = post_time

        self.api_url = api_url
        self.threads = {d['fork']: d for d in threads}

        self.comments_df = None

    def load_comments(
        self,
        forks: Union[List, int] = [0, 1, 2],
        mode: str = 'once',
        hop_rate: float = .5,
        check: bool = True,
        **tqdm_kwargs
    ):
        assert type(forks) == int or all([type(fork) == int for fork in forks])
        assert mode in ['once', 'roughly', 'exactly']

        if type(forks) == int:
            forks = [forks]

        def fetch_comments(forks, when=None):
            params_dict = {
                fork: dict(
                    **{
                        'thread':    self.threads[fork]['id'],
                        'fork':      self.threads[fork]['fork'],
                        'threadkey': self.threads[fork]['threadkey'],
                        'when': when
                    },
                    **base_params
                )
                for fork in forks
            }

            req = [
                {k: params_dict[fork] for k in ['thread', 'thread_leaves']}
                for fork in forks
            ]

            res = requests.get(self.api_url, data=json.dumps(req))
            comments = [d['chat'] for d in json.loads(res.text) if 'chat' in d]

            return comments

        def convert_to_df(comments):
            comments_dict = {}
            for com in comments:
                default_items = {
                    'user_id':   None,
                    'date_usec': 0,
                    'anonymity': 0,
                    'fork':      0,
                    'score':     0,
                    'mail':      '',
                    'position':  basic_commands['position'][0],
                    'size':      basic_commands['size'][0],
                    'color':     basic_commands['color'][0]
                }
                for k, v in default_items.items():
                    if k not in com:
                        com[k] = v

                if com['mail']:
                    cmds = com['mail'].split()
                    if '184' in cmds:
                        if com['anonymity'] != 1:
                            print('184 error.')
                        _ = cmds.pop(cmds.index('184'))

                    cmds_set = set(cmds)
                    check_dict = {
                        'position': cmds_set & set(basic_commands['position']),
                        'size':     cmds_set & set(basic_commands['size']),
                        'color':    cmds_set & set(basic_commands['color'])
                    }

                    for k, v in check_dict.items():
                        if v:
                            com[k] = cmds.pop(cmds.index(v.pop()))

                    com['mail'] = ' '.join(cmds)

                comment_id = f'{com["fork"]}-{com["no"]}'

                vpos = '0' if com['vpos'] < 0 else str(com['vpos'])
                write_time = float(f'{com["date"]}.{com["date_usec"]}')
                video_time = float(f'{vpos[:-2]}.{vpos[-2:]}')

                datas = {
                    'comment':    com['content'],
                    'user_id':    com['user_id'],
                    'write_time': write_time,
                    'video_time': video_time,
                    '184':        com['anonymity'],
                    'position':   com['position'],
                    'size':       com['size'],
                    'color':      com['color'],
                    'command':    com['mail'],
                    'score':      com['score']
                }
                datas = {
                    k: v if v is not None else np.nan
                    for k, v in datas.items()
                }

                comments_dict[comment_id] = datas

            comments_df = pd.DataFrame.from_dict(comments_dict, orient='index')
            if comments_dict:
                comments_df.sort_values('write_time', inplace=True)
                comments_df.index.name = 'comment_id'

            return comments_df

        def merge_df(a_df, b_df):
            if a_df.empty and b_df.empty:
                return sorted([a_df, b_df], key=lambda x: len(x.columns))[-1]
            elif a_df.empty:
                return b_df
            elif b_df.empty:
                return a_df
            else:
                ab_df = pd.merge(
                    a_df.reset_index(), b_df.reset_index(), how='outer'
                ).set_index('comment_id').sort_values('write_time')
                return ab_df

        def check_df(comments_df, tgt_forks):
            got_forks = set(map(int, set(comments_df.index.str[0])))
            tgt_forks = set(tgt_forks)
            # 読み込みできなかった fork は最初から存在していないものとみなして消去
            for fork in tgt_forks.copy():
                if fork not in got_forks:
                    tgt_forks.remove(fork)

            # 全件読み込めている fork は消去
            for fork in tgt_forks.copy():
                fork_df = comments_df[comments_df.index.str[0] == str(fork)]
                cids = sorted(list(map(int, fork_df.index.str[2:])))
                if cids[-1] == len(cids):
                    tgt_forks.remove(fork)

            return sorted(list(tgt_forks))

        now_time = datetime.datetime.now().timestamp()
        now_df = convert_to_df(fetch_comments(forks))

        comments_df = now_df
        forks = check_df(comments_df, forks)

        if mode == 'once' or not forks:
            self.comments_df = comments_df
            if check:
                self.check_comments()

            return comments_df

        # 1時間前のコメントを基準にしてそこから遡って読み込む
        tmp_time = now_time - 60*60
        tmp_df = convert_to_df(fetch_comments(forks))

        comments_df = merge_df(comments_df, tmp_df)
        forks = check_df(comments_df, forks)

        try_num = 1+1
        with tqdm(total=int(now_time-self.post_time), **tqdm_kwargs) as pbar:
            while forks:
                try_num += 1
                fork2tmp = {
                    fork: tmp_df[tmp_df.index.str[0] == str(fork)]
                    for fork in forks
                }
                tgt_time = max([
                    fork2tmp[fork].write_time[int((len(fork2tmp[fork])-1)*hop_rate)]
                    for fork in forks
                    if not fork2tmp[fork].empty
                ]+[-1])
                if tgt_time == -1:
                    sleep(3)
                    continue
                tgt_df = convert_to_df(fetch_comments(forks, when=tgt_time))
                if tgt_df.empty:
                    break

                comments_df = merge_df(comments_df, tgt_df)
                forks = check_df(comments_df, forks)

                pbar.set_postfix(
                    date=str(datetime.datetime.fromtimestamp(tgt_time).date()),
                )
                pbar.set_description(f'Loading roughly [{try_num}]')
                pbar.update(int(tmp_time-tgt_time))

                comp_list = [
                    not (
                        set(tgt_df[tgt_df.index.str[0] == str(fork)].index) - \
                        set(tmp_df[tmp_df.index.str[0] == str(fork)].index)
                    )
                    for fork in forks
                ]
                if all(comp_list):
                    break

                tmp_time, tmp_df = tgt_time, tgt_df

            pbar.update(pbar.total-pbar.n)

        if mode == 'exactly':
            fork2com = {
                fork: comments_df[comments_df.index.str[0] == str(fork)]
                for fork in forks
            }
            unload_cids = {
                fork:
                    sorted(list(
                        set(range(1, len(fork2com[fork])+1)) - \
                        set(map(int, fork2com[fork].index.str[2:]))
                    ))
                for fork in forks
            }
            # 一度に読み込める大体のコメントの数(目安)
            avg_cnum = {
                0: min(500, self.video_counter['comment']//10),
                1: 1000,
                2: 100
            }
            w_len = {k: int(v*.8) for k, v in avg_cnum.items()}

            tgt_cids = {fork: [] for fork in forks}
            for fork in forks:
                r_cid = unload_cids[fork][-1]
                l_cid, m_cid = r_cid-2*w_len[fork], r_cid-w_len[fork]

                if m_cid < 0:
                    tgt_cids[fork].append(r_cid)
                    continue
                else:
                    tgt_cids[fork].append(m_cid)

                for cid in unload_cids[fork][::-1]:
                    if l_cid >= cid:
                        r_cid = l_cid
                        l_cid, m_cid = r_cid-2*w_len[fork], r_cid-w_len[fork]

                        if r_cid < 0:
                            break

                        if m_cid < 0:
                            tgt_cids[fork].append(r_cid)
                            break
                        else:
                            tgt_cids[fork].append(m_cid)

            tgt_whens = {}
            for fork in forks:
                cids = tgt_cids[fork]
                com_cids = sorted(list(map(int, fork2com[fork].index.str[2:])))
                tmp = []
                for cid in cids:
                    for ccid in com_cids:
                        if ccid >= cid:
                            tmp.append(f'{fork}-{ccid}')
                            break

                tgt_whens[fork] = fork2com[fork].loc[tmp, :].write_time.values

            for fork in forks.copy():
                for when in tqdm(
                    tgt_whens[fork], desc=f'{fork}-Loading exactly', **tqdm_kwargs
                ):
                    tgt_df = convert_to_df(
                        fetch_comments(forks, when=when)
                    )
                    comments_df = merge_df(comments_df, tgt_df)
                    forks = check_df(comments_df, forks)

                    if not forks:
                        break

        self.comments_df = comments_df

        if check:
            self.check_comments()

    def check_comments(self):
        if self.comments_df is not None:
            total_df = self.comments_df
            total_uids = set(total_df.user_id)
            total_unum, total_cnum = len(total_uids), len(total_df)

            forks = sorted(list(set([cid[0] for cid in total_df.index])))
            forks_dfs = [total_df[total_df.index.str[0] == fork] for fork in forks]

            print('=== total comments ===')
            print('user number:', total_unum)
            print('comment number:', total_cnum)
            print(f'comment / user: {total_cnum/total_unum:.2f}')
            print('------')
            print(
                'acquisition rate:',
                f'{total_cnum/sum([int(df.index[-1][2:]) for df in forks_dfs]):.2%}'
            )
            if forks:
                print()

            for fork, fork_df in zip(forks, forks_dfs):
                fork_uids = set(fork_df.user_id)
                fork_cnum, fork_unum = len(fork_df), len(fork_uids)

                print(f'=== comments: {fork} ===')
                print('user number:', fork_unum)
                print('comment number:', fork_cnum)
                print(f'comment / user: {fork_cnum/fork_unum:.2f}')
                print('------')
                print(
                    'acquisition rate:',
                    f'{fork_cnum/int(fork_df.index[-1][2:]):.2%}'
                )
                if fork != forks[-1]:
                    print()

    def sort_comments(
        self,
        sort_items_list: List = ['write_time'],
        ascending: bool = True
    ):
        if self.comments_df is not None:
            tags, ascendings = [], []
            for items in sort_items_list:
                if type(items) == str:
                    tags.append(items)
                    ascendings.append(ascending)
                elif type(items) == tuple:
                    tags.append(items[0])
                    if items[1] in [1, True]:
                        ascendings.append(True)
                    elif items[1] in [-1, False]:
                        ascendings.append(False)
                    else:
                        ascendings.append(ascending)

            sorted_df = self.comments_df.sort_values(
                tags[::-1], ascending=ascendings[::-1]
            )

            return sorted_df

    def video_html(self, w: int = 640, h: int = 360):
        video_id = self.video_id
        video_title = self.video_title
        html = f'''
            <script
              type="application/javascript"
              src="https://embed.nicovideo.jp/watch/{video_id}/script?w={w}&h={h}">
            </script>
            <noscript>
                <a href="https://www.nicovideo.jp/watch/{video_id}">{video_title}</a>
            </noscript>
        '''
        return html
