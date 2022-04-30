import requests
import json
import datetime
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image


def fetch_ranking_info(url: str):
    source = requests.get(url)
    soup = BeautifulSoup(source.text, 'html.parser')

    info = {}
    for i, elem in enumerate(soup.find_all('div', class_='NC-VideoMediaObject')):
        title = elem.h2.text.lstrip()
        vid = elem.attrs['data-video-id']
        thumbnail = elem.find(
            'div', class_='NC-Thumbnail-image'
        ).attrs['data-background-image']
        thumbnail = thumbnail
        if thumbnail.split('/')[:-1].count('.') == 2:
            thumbnail = '.'.join(thumbnail.split('.')[:-2])
        post = elem.find('span', class_='NC-VideoRegisteredAtText-text').text
        view, comment, like, mylist, _ = [
            counter.text for counter in elem.find_all('div', 'NC-VideoMetaCount')
        ]
        info[i] = {
            'url': f'https://www.nicovideo.jp/watch/{vid}',
            'title': title.strip(),
            'thumbnail': thumbnail,
            'post': post.strip(),
            'view': view,
            'comment': comment,
            'like': like,
            'mylist': mylist
        }
    
    return info if info else None


def fetch_video_info(url: str):
    source = requests.get(url)
    soup = BeautifulSoup(source.text, 'html.parser')

    video_datas = json.loads(
        soup.select_one('#js-initial-watch-data').get('data-api-data')
    )['video']
    title = video_datas['title']
    thumbnail = video_datas['thumbnail']['url']
    post = datetime.datetime.strptime(
        video_datas['registeredAt'], '%Y-%m-%dT%H:%M:%S+09:00'
    ).strftime('%Y/%-m/%-d %H:%M')
    view = video_datas['count']['view']
    comment = video_datas['count']['comment']
    like = video_datas['count']['like']
    mylist = video_datas['count']['mylist']
    info = {
        'url': url,
        'title': title,
        'thumbnail': thumbnail,
        'post': post,
        'view': view,
        'comment': comment,
        'like': like,
        'mylist': mylist
    }
    return info


def url2img(url: str):
    return Image.open(BytesIO(requests.get(url).content))