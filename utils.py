import json
from datetime import datetime

import numpy as np
import pandas as pd
import requests

import streamlit as st
from streamlit_cookies_controller import CookieController

cookies = CookieController()

def to_float(lst):
    ls = []
    for x in lst:
        try:
            ls.append(float(x.replace(',','')))
        except Exception as e:
            ls.append(x)
    return ls


def set_cookies(key, value):
    cookies.set(key,value)

def split_str(t):
    return [x.strip() for x in t.split(',') if x.strip() != '']

def filter_date(o_data, filtered_keys):
    for x in o_data:
        for key in filtered_keys:
            o_data[x].pop(key)
    return o_data

def merge_details(xdf, changes):
    df = changes.where(changes['Split'] == True).dropna()
    options = set(df['Type'].to_list())

    if len(options) == 2 and 'FutureCredit' in options and 'Credit' in options:
        fc_index = df.index[df['Type'] == 'FutureCredit'].to_list()
        c_index = df.index[df['Type'] == 'Credit'].to_list()
        return True, fc_index, c_index
    else:
        return False, [],[]

def merge_dues(fc_index, c_index, changes):
    df = changes.where(changes['Split'] == True).dropna()
    df = df.to_dict()

    if 'Split' in df:
        df.pop('Split')

    total_due, total_got = 0, 0
    for x in df['Account']:
        df['Tags'][x] = df['Tags'][x].split(',')
        if x in fc_index:
            total_due += df['Amount'][x]
        else:
            total_got += df['Amount'][x]
    uncleared = []
    got_due = total_due - total_got
    for x in df['Account']:
        if x in fc_index:
            if total_got - df['Amount'][x] > 0:
                df['Tags'][x].append('Cleared')
                total_got -= df['Amount'][x]
            else:
                uncleared.append(x)
        else:
            df['Tags'][x].append(f'Due {got_due} cleared for : {list(set(fc_index) - set(uncleared))}')

    if len(uncleared):
        st.warning(f'Unable to clear for Amount : {total_got}, all Dues : {uncleared}')

    if st.session_state['DF_UPDATES'] is not None:
        updates = st.session_state['DF_UPDATES'].to_dict()
        updates = concat_datas(updates, df)
        st.session_state['DF_UPDATES'] = pd.DataFrame(updates).dropna()
    else:
        st.session_state['DF_UPDATES'] = pd.DataFrame(df).dropna()


def concat_datas(o_data, n_data):
    o_data['Account'].update(n_data['Account'])
    o_data['Amount'].update(n_data['Amount'])
    o_data['Tags'].update(n_data['Tags'])
    o_data['Date'].update(n_data['Date'])
    o_data['Mode'].update(n_data['Mode'])
    o_data['Type'].update(n_data['Type'])
    o_data['From/To'].update(n_data['From/To'])
    return o_data

def get_different_from_df(df, changes):
    return changes[~df.apply(tuple, 1).isin(changes.apply(tuple, 1))]

def check_split(xdf,changes, config):
    df = changes.where(changes['Split'] == True).dropna()
    split_source_dict = df.to_dict()
    validate_df_changes(xdf,changes)
    ndf = {'Account':{},'Date':{},'From/To':{},'Amount':{},'Mode':{},'Type':{},'Tags':{}}
    for s_key in split_source_dict['Amount']:
        for indx in range(config['quantity']):
            dt = datetime.strptime(s_key,"%Y-%m-%d %H:%M:%S")
            acc = split_source_dict['Account'][s_key]
            tags = split_source_dict['Tags'][s_key]

            if indx == 0:
                key = s_key
                frm_to = split_source_dict['From/To'][s_key]
            else:
                key = str(dt.replace(minute=dt.minute - (1*indx) if dt.minute > 5 else 3,second=np.random.randint(0,60)))
                while key in ndf['Account']:
                    key = str(
                        dt.replace(minute=dt.minute - (1 * indx) if dt.minute > 5 else 3, second=np.random.randint(0, 60)))
                frm_to = config['splits'][indx]['user']

            amount = 0
            if config['type'] == 'Percentage':
                amount = round((config['splits'][indx]['amount'] * split_source_dict['Amount'][s_key]) / 100,2)
            elif config['type'] == 'Manual':
                amount = config['splits'][indx]['amount']
            elif config['type'] == 'Equally':
                amount = round(split_source_dict['Amount'][s_key] / config['quantity'],2)

            ndf['Account'][key] = acc
            ndf['Date'][key] = datetime.strptime(key,"%Y-%m-%d %H:%M:%S").strftime("%d-%b, %I:%M %p")
            ndf['Amount'][key] = amount
            ndf['From/To'][key] = frm_to
            ndf['Mode'][key] = 'Split' if indx != 0 else split_source_dict['Mode'][s_key]
            ndf['Type'][key] = 'FutureCredit' if indx != 0 else split_source_dict['Type'][s_key]
            ndf['Tags'][key] = split_str(tags) + (['Split','New Split',s_key] if indx != 0 else [])
            st.write(ndf['Tags'][key])
    ndf = pd.DataFrame(ndf)

    if st.session_state['DF_UPDATES'] is not None:
        st.session_state['DF_UPDATES'] = ndf.combine_first(st.session_state['DF_UPDATES'])
    else:
        st.session_state['DF_UPDATES'] = ndf

    # st.write(st.session_state['DF_UPDATES'])

def validate_df_changes(df,changes):
    if df.compare(changes).shape[0] > 0:
        df['Tags'] = df['Tags'].apply(split_str)
        changes['Tags'] = changes['Tags'].apply(split_str)

        data = df.to_dict()
        changed = get_different_from_df(df,changes).to_dict()

        if st.session_state['DF_UPDATES'] is not None and 'Split' in st.session_state['DF_UPDATES']:
            st.session_state['DF_UPDATES'].pop('Split')
        if 'Split' in data:
            data.pop('Split')
        if 'Split' in changed:
            changed.pop('Split')

        if st.session_state['DF_UPDATES'] is not None:
            updates = st.session_state['DF_UPDATES'].to_dict()
            updates = concat_datas(updates, changed)
            st.session_state['DF_UPDATES'] = pd.DataFrame(updates).dropna()
        else:
            st.session_state['DF_UPDATES'] = pd.DataFrame(changed).dropna()

def update_split_data(changes):
    updates_df = st.session_state['DF_UPDATES']
    if updates_df is not None:
        split_source = updates_df.to_dict()
        df = updates_df[updates_df['Tags'].str.contains('New Split', regex=False)]
        df_dct = df.to_dict()
        for index in df_dct['Account']:
            for tag in df_dct['Tags'][index]:
                if tag in split_source['Amount']:
                    # split_source['Amount'][tag] -= df_dct['Amount'][index]
                    split_source['Tags'][tag].append(f'Split : {df_dct["Amount"][index]}')
                    break
        st.session_state['DF_UPDATES'] = pd.DataFrame(split_source).dropna()

def save_df(df, changes):
    validate_df_changes(df, changes)
    update_split_data(changes)
    # st.write(st.session_state['DF_UPDATES'])
    df = st.session_state['DF_UPDATES']
    # st.write(df)
    # # st.write(changes)

    has_new_memo = save_memo()

    if df is not None:
        json_df = df.to_dict()
        update_json = {}
        for index in json_df['Account']:
            bank, acc = json_df['Account'][index].split(' ')
            acc = acc.replace("(","").replace(")",'')
            key = str(index)

            path = f"{bank}~{acc}~{key}"
            update_json[path] = {
                    'type': json_df['Type'][index],
                    'mode': json_df['Mode'][index],
                    'tags': [i.strip() for i in json_df['Tags'][index] if i.strip() != ''],
                    'to_from': json_df['From/To'][index],
                    'amount': json_df['Amount'][index]
                }
            if 'New Split' in update_json[path]['tags']:
                update_json[path]['accountType'] = 'Split'
                update_json[path]['time'] = datetime.strptime(key,"%Y-%m-%d %H:%M:%S").strftime("%d-%b, %I:%M %p")
                update_json[path]['refNo'] = update_json[path]['tags'][2]
                update_json[path]['account'] = json_df['Account'][index].split('(')[1].split(')')[0]
                update_json[path]['gps'] = ''

                ind = update_json[path]['tags'].index('New Split')
                if ind:
                    update_json[path]['tags'].pop(ind)
                    update_json[path]['tags'].pop(ind)

            elif 'New Trans' in update_json[path]['tags']:
                update_json[path]['accountType'] = json_df['Type'][index]
                update_json[path]['time'] = json_df['Date'][index]
                update_json[path]['refNo'] = ''
                update_json[path]['account'] = json_df['Account'][index]
                update_json[path]['gps'] = ''

                if (update_json[path]['account'] == 'XXXX (XXXX)' or
                    update_json[path]['to_from'] == 'X' or
                     update_json[path]['mode'] == ''):
                    st.error(f'Unable to Create New Transaction : {index}')
                    update_json.pop(path)
                else:
                    ind = update_json[path]['tags'].index('New Trans')
                    if ind is not None:
                        update_json[path]['tags'].pop(ind)

        st.write(update_json)
        # res = requests.post("http://127.0.0.1:5000/update-records",json=update_json)
        res = requests.post("https://finance---api.vercel.app/update-records",json=update_json, headers={'USER':st.session_state['USER']})
        if res.status_code == 200:
            st.session_state['TAGS_EDITABLE'] = False
            st.session_state['DF_UPDATES'] = None
            with open('info.json','r') as f:
                data = json.load(f)
            with open('info.json', 'w') as f:
                data[st.session_state['USER']] = {}
                json.dump({}, f)

            st.toast('Data Saved Successfully')

        else:
            st.warning('Unable to save DF, some error occurred')

    elif has_new_memo:
        with open('info.json', 'r') as f:
            data = json.load(f)
        with open('info.json', 'w') as f:
            data[st.session_state['USER']]['Memo'] = st.session_state['MEMOS']
            json.dump({}, f)

        st.toast('Memo Saved Successfully')


def save_memo():
    if 'MEMO_KEY' in st.session_state:
        text = st.session_state['memo']
        key = st.session_state['MEMO_KEY']

        st.session_state['MEMOS'][key] = text

        res = requests.post("https://finance---api.vercel.app/update-memo", json={key:text},
                            headers={'USER': st.session_state['USER']})

        if res.status_code == 200:
            st.session_state.pop('MEMO_KEY')
            return True
        else:
            st.warning('Unable to save the memo!')

    return False

def new_trans(row):
    ndf = pd.DataFrame(row).set_index('Key')
    if st.session_state['DF_UPDATES'] is not None:
        st.session_state['DF_UPDATES'] = st.session_state['DF_UPDATES'].combine_first(ndf)
    else:
        st.session_state['DF_UPDATES'] = ndf
