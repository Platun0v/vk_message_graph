from vk_api import VkApi
import datetime
import requests
from matplotlib import pyplot as plt

auth_url = 'https://oauth.vk.com/token?' \
           'grant_type=password&client_id=2274003&client_secret=hHbZxrka2uZ6jB1inYsH&' \
           'username={login}&password={password}'


class Program:
    def __init__(self, api, user_id):
        self.api = api
        self.peer_id = None
        self.user_id = int(user_id)
        self.usernames = {}

    def get_peer_id(self):
        peers = []
        offset = 0
        prev = -1
        while True:
            if offset != prev:
                peers = self.next_peers(offset)
                prev = offset

            it = read(from_=-1, to=len(peers) - 1, num=True,
                      s_in='Введите номер переписки, которую хотите сохранить, или -1, чтобы выести следующую десятку: ',
                      s_out='Введено неверное значение', )
            if it == -1:
                offset += 10
                continue

            self.peer_id = peers[it][0]
            data = self.get_data()

            text_len = read(lst=[0, 1], num=True,
                            s_in='Введите 0, если хотите график по количеству сообщений, '
                                 'или 1, если хотите график по количеству отправленных символов: ')
            data = self.preprocess_data(data, text_len)

            self.make_graph(data)
            break

    def next_peers(self, offset):
        peers_data = self.api.messages.getConversations(count=10, offset=offset)
        peers = []
        for e in peers_data['items']:
            peer = e['conversation']['peer']
            if peer['type'] == 'chat':
                peers.append([peer['id'], self.get_chat_name(peer['local_id'])])
            elif peer['type'] == 'user':
                user = self.get_username(peer['id'])
                peers.append([peer['id'], f"{user['first_name']} {user['second_name']}"])

        for i, e in enumerate(peers):
            print(f"{i}. {e[1]}")
        return peers

    def get_data(self):
        with open('execute.txt', 'r') as f:
            execute_code = ''.join(f.readlines())

        start = 0
        count = 2500
        print('Downloading data... ', end='')
        data = []
        while True:
            response = self.api.execute(code=execute_code % (self.peer_id, count, start))
            if not response:
                break
            data.extend(response)
            start += 2500

        data.sort(key=lambda x: x['date'])  # date from_id text
        print('Data downloaded')
        return data

    def preprocess_data(self, data, text_len=False):
        new_data = {}
        delta = 1
        for message in data:
            if text_len:
                delta = len(message['text'])
                if delta > 250:
                    delta = 0
            from_id = message['from_id']
            cur_date = message['date']
            if from_id not in new_data.keys():
                new_data[from_id] = {'date': [datetime.datetime.fromtimestamp(cur_date)],
                                     'message_cnt': [delta], }
            else:
                prev_date = new_data[from_id]['date'][-1].timestamp()
                if cur_date - prev_date <= 60 * 10:
                    new_data[from_id]['message_cnt'][-1] += delta
                else:
                    new_data[from_id]['date'].append(datetime.datetime.fromtimestamp(cur_date))
                    new_data[from_id]['message_cnt'].append(new_data[from_id]['message_cnt'][-1] + delta)

        last_date = datetime.datetime.fromtimestamp(data[-1]['date'])

        for user_id in new_data.keys():
            new_data[user_id]['date'].append(last_date)
            new_data[user_id]['message_cnt'].append(new_data[user_id]['message_cnt'][-1])

        return new_data

    def make_graph(self, data):
        for user_id in data.keys():
            username = lambda x: f"{x['first_name']} {x['second_name']}"
            plt.plot_date(x=data[user_id]['date'],
                          y=data[user_id]['message_cnt'],
                          linestyle='-', marker='None',
                          label=username(self.get_username(user_id))
                          )

        plt.legend()
        plt.show()

    def get_username(self, user_id):
        if user_id in self.usernames.keys():
            return self.usernames[user_id]
        try:
            user = self.api.users.get(user_ids=user_id)[0]
        except Exception:
            user = {'first_name': 'DELETED', 'last_name': 'DELETED'}
        user = {'first_name': user['first_name'], 'second_name': user['last_name']}
        self.usernames[user_id] = user
        return user

    def get_chat_name(self, chat_id):
        return self.api.messages.getChat(chat_id=chat_id)['title']


def read_num(s='> '):
    while True:
        n = input(s)
        try:
            n = int(n)
            return n
        except ValueError:
            print('Invalid value entered')


def read_letter(s='> '):
    while True:
        letter = input(s)
        if len(letter) != 1:
            print('Invalid value entered')
            continue

        letter = letter.lower()
        if 'a' <= letter <= 'z':
            pass
        else:
            print('Invalid value entered')
            continue

        return letter


def read(from_=None, to=None, lst=None, check_fun=None, kwargs=None,
         s_in='> ', s_out='Unexpected value',
         letter=False, num=False):

    if kwargs is None:
        kwargs = {}

    if check_fun is None:
        if lst is None:
            if from_ is None:
                check_fun = lambda x: True
            else:
                if isinstance(from_, str):
                    lst = [chr(i) for i in range(ord(from_), ord(to) + 1)]
                elif isinstance(from_, int):
                    lst = [i for i in range(from_, to + 1)]

    if letter:
        fun = read_letter
    elif num:
        fun = read_num
    else:
        fun = input

    while True:
        inp = fun(s_in)
        if (lst and inp in lst) or (check_fun and check_fun(inp, **kwargs)):
            return inp
        else:
            print(s_out)


def auth():
    def check_pass(password, login):
        try:
            resp = requests.get(auth_url.format(login=login, password=password)).json()
            if 'error' in resp.keys():
                return False
        except:
            return False

        return True

    login = read(s_in='Введите логин: ')
    password = read(s_in='Введите пароль: ', s_out='Не удалось авторизоваться, попробуй еще раз...',
                    check_fun=check_pass, kwargs={'login': login}, )

    resp = requests.get(auth_url.format(login=login, password=password)).json()

    vk = VkApi(token=resp['access_token'])
    api = vk.get_api()
    return api, resp['user_id']


def main():
    api, user_id = auth()
    program = Program(api, user_id)
    while True:
        program.get_peer_id()


if __name__ == '__main__':
    main()
