import calendar
import json
import locale
import math

import numpy as np
import requests
import streamlit as st
import pandas as pd
from datetime import timedelta, datetime,date

from main import cookies

# USER = cookies.get('finance-user')
TAB_LIST = ['Monthly Summary','Detailed Summary']
MONTH_LIST = []
CURR_TIME = datetime.now()
CURR_MONTH = CURR_TIME.month
CURR_YEAR = CURR_TIME.year

def to_format(s,format):
    lst = []
    for x in s:
        lst.append(x.strftime(format))
    return lst

def to_float(lst):
    ls = []
    for x in lst:
        try:
            ls.append(float(x.replace(',','')))
        except Exception as e:
            ls.append(x)
    return ls

for x in range(5):
    if CURR_MONTH < 1:
        CURR_YEAR-=1
        CURR_MONTH = 12
    _,last = calendar.monthrange(CURR_YEAR,CURR_MONTH)
    MONTH_LIST.append(date(CURR_YEAR,CURR_MONTH,last))
    CURR_MONTH-=1

DF_COLUMNS = ['Key','Account','Date','From/To','Amount','Mode','Type','Tags']

PAYMENT_TAGS = ()

def split_str(t):
    return [x.strip() for x in t.split(',')]

def save_changes():
    pass

def check_split(xdf,changes):
    print("Here\n\n")
    df = changes.where(changes['Split'] == True).dropna()
    validate_df_changes(xdf,changes)
    ndf = pd.DataFrame([[]],DF_COLUMNS)
    for key in df.index.to_list():
        dt = datetime.strptime(key,"%Y-%m-%d %H:%M:%S")
        fdf = df[df.index.isin([str(key)])]
        acc = fdf['Account'].to_list()[0]
        tags = fdf['Tags'].to_list()[0]
        row = {
                'Key': [str(dt.replace(minute=dt.minute + 1 if dt.minute < 55 else 56,second=np.random.randint(0,60)))],
                'Account': [acc],
                'Date': ['X'],
                'From/To': ['X'],
                'Amount': [0],
                'Mode': ['Split'],
                'Type': ['FutureCredit'],
                'Tags': [tags.split(' , ') + ['Split','New Split',key]],
            }
        if ndf.shape[0] == 0:
            ndf = pd.DataFrame(row)
        else:
            ndf = pd.concat([ndf,pd.DataFrame(row)],ignore_index=True)

    ndf = ndf.set_index('Key').dropna()

    if st.session_state['DF_UPDATES'] is not None:
        st.session_state['DF_UPDATES'] = st.session_state['DF_UPDATES'].combine_first(ndf)
    else:
        st.session_state['DF_UPDATES'] = ndf
    # st.session_state['DF_UPDATES'].reindex('Key')

def validate_df_changes(df,changes):
    if df.compare(changes).shape[0] > 0:
        print("Triggered")

        if st.session_state['DF_UPDATES'] is not None and 'Split' in st.session_state['DF_UPDATES'].columns:
            st.session_state['DF_UPDATES'].drop('Split',axis=1, inplace=True)
        if 'Split' in df.columns:
            df.drop('Split',axis=1, inplace=True)
        if 'Split' in changes.columns:
            changes.drop('Split',axis=1, inplace=True)
        #
        # st.write(str(~df.apply(tuple,1).isin(changes.apply(tuple,1))))
        # st.write(df.apply(str,1))
        # st.write(changes.apply(str,1))


        df3 = changes[~df.apply(tuple,1).isin(changes.apply(tuple,1))]

        df3['Tags'] = df3['Tags'].apply(split_str)

        # st.dataframe(df,hide_index=False)
        # st.dataframe(changes,hide_index=False)
        # st.dataframe(df3,hide_index=False)

        if st.session_state['DF_UPDATES'] is not None:
            if 'Split' in st.session_state['DF_UPDATES'].columns:
                st.session_state['DF_UPDATES'].drop('Split',axis=1, inplace=True)

            st.session_state['DF_UPDATES'] = df3.combine_first(st.session_state['DF_UPDATES'])
        else:
            st.session_state['DF_UPDATES'] = df3
        # st.session_state['DF_UPDATES'].set_index('Key')
        if 'Split' in st.session_state['DF_UPDATES'].columns:
            st.session_state['DF_UPDATES'].drop('Split',axis=1, inplace=True)

def update_split_data(changes):
    df = st.session_state['DF_UPDATES']
    if df is not None:
        df = df[df['Tags'].str.contains('New Split', regex=False)]
        df = df.reset_index()
        df_dct = df.to_dict()
        for index in df_dct['Key']:

            if st.session_state['DF_UPDATES'][st.session_state['DF_UPDATES'].index == df_dct['Tags'][index][2]].shape[0] > 0:
                ndf = st.session_state['DF_UPDATES'][st.session_state['DF_UPDATES'].index == df_dct['Tags'][index][2]]
                ndf['Tags'] = ndf['Tags'].apply(' , '.join)
            else:
                ndf = changes[changes.index == df_dct['Tags'][index][2]]
            # st.write(ndf)
            if ndf.shape[0] > 1:
                ndf = ndf.iloc[[1]]

            ndf['Amount'] = ndf['Amount'] - df_dct['Amount'][index]
            ndf['Tags'] = ndf['Tags'] + f' , Split : {df_dct["Amount"][index]}'
            st.session_state['DF_UPDATES']['Tags'] = st.session_state['DF_UPDATES']['Tags'].apply(tuple)
            # st.write("hi",st.session_state['DF_UPDATES'])

            ndf['Tags'] = ndf['Tags'].apply(lambda x: x.split(' , '))
            # st.write("df",ndf)
            if ndf.index.values in st.session_state['DF_UPDATES'].index.values:
                st.session_state['DF_UPDATES'].update(ndf)
            else:
                st.session_state['DF_UPDATES'] = pd.concat([st.session_state['DF_UPDATES'],ndf],ignore_index=False)

            # st.write(st.session_state['DF_UPDATES']['Tags'])
            st.session_state['DF_UPDATES']['Tags'] = st.session_state['DF_UPDATES']['Tags'].apply(list).apply(lambda x: list(filter(lambda y: y != "", x)) if "" in x else x)

        # st.write(st.session_state['DF_UPDATES'])

def merge_dues(src_key, tgt_key, crrnt_key, changes):
    changes = changes.reset_index()
    changes.drop('Split',axis=1, inplace=True)

    tgt_df = changes[changes['Key'] == tgt_key]
    crrnt_df = changes[changes['Key'] == crrnt_key]

    tgt_df['Tags'] = tgt_df['Tags'] + f' , Due {crrnt_df["Amount"].to_list()[0]} cleared for Record {src_key}'
    crrnt_df['Tags'] = crrnt_df['Tags'] + f' , Deleted'


    if st.session_state['DF_UPDATES'] is None:
        st.session_state['DF_UPDATES'] = pd.concat([crrnt_df,tgt_df],ignore_index=True)
    else:
        st.session_state['DF_UPDATES'] = pd.concat([st.session_state['DF_UPDATES'],crrnt_df,tgt_df],ignore_index=True)

    st.session_state['DF_UPDATES'] = st.session_state['DF_UPDATES'].set_index('Key')

    st.session_state['DF_UPDATES']['Tags'] = st.session_state['DF_UPDATES']['Tags'].apply(lambda x: x.split(' , '))


def save_df(df, changes):

    st.session_state['TAGS_EDITABLE'] = False
    validate_df_changes(df, changes)
    update_split_data(changes)
    df = st.session_state['DF_UPDATES']
    # st.write(df)
    # st.write(changes)
    if df is not None:
        df = df.reset_index()
        json_df = df.to_dict()
        update_json = {}
        for index in json_df['Key']:
            bank, acc = json_df['Account'][index].split(' ')
            acc = acc.replace("(","").replace(")",'')
            key = str(json_df['Key'][index])

            path = f"{bank}~{acc}~{key}"
            update_json[path] = {
                    'type': json_df['Type'][index],
                    'mode': json_df['Mode'][index],
                    'tags': [i for i in json_df['Tags'][index] if i != ''],
                    'to_from': json_df['From/To'][index],
                    'amount': json_df['Amount'][index]
                }
            if 'New Split' in update_json[path]['tags']:
                update_json[path]['accountType'] = 'Split'
                update_json[path]['time'] = datetime.strptime(key,"%Y-%m-%d %H:%M:%S").strftime("%d-%b, %I:%M %p")
                update_json[path]['refNo'] = update_json[path]['tags'][2]
                update_json[path]['account'] = json_df['Account'][index].split('(')[1].split(')')[0]
                update_json[path]['gps'] = ''

                update_json[path]['tags'].pop()
                update_json[path]['tags'].pop()


        # res = requests.post("http://127.0.0.1:5000/update-records",json=update_json)
        res = requests.post("https://finance---api.vercel.app/update-records",json=update_json, headers={'USER':st.session_state['USER']})
        if res.status_code == 200:
            st.session_state['DF_UPDATES'] = None
            with open('info.json','r') as f:
                data = json.load(f)
            with open('info.json', 'w') as f:
                data[st.session_state['USER']] = {}
                json.dump({}, f)

def set_cookies(key, value):
    cookies.set(key,value)

def generate_basic_ui(user, paymentInfo):

    st.session_state['USER'] = user

    if 'TAGS_EDITABLE' not in st.session_state:
        st.session_state['TAGS_EDITABLE'] = False
    if 'DF_UPDATES' not in st.session_state:
            st.session_state['DF_UPDATES'] = None

    st.session_state['TAGS_EDITABLE'] = st.session_state['TAGS_EDITABLE'] if 'Edit_BTN' not in st.session_state else st.session_state['Edit_BTN']
    hd_cols = st.columns([1,0.1])

    with hd_cols[0]:
        st.header(f"Hello, {user}")
    with hd_cols[1]:
        st.button(icon="🔄",on_click=set_cookies,args=('reload',True),label=' ')

    tabs = st.tabs(TAB_LIST)
    data=[]
    for bank in paymentInfo:
        if bank == 'Stash': continue
        for acc in paymentInfo[bank]:
            for key in paymentInfo[bank][acc]:
                trans = paymentInfo[bank][acc][key]
                try:
                    data.append((key, f"{bank} ({trans['account']})", trans['time'], trans['to_from'], trans['amount'],trans['mode'], trans['type'], [] if 'tags' not in trans else trans['tags']))
                except:
                    st.write(trans)
    with tabs[0]:
        df = pd.DataFrame(data,columns=DF_COLUMNS)
        cols = st.columns([0.75,0.25],gap="large")
        with cols[1]:
            selectedMonth = st.selectbox("X",[f"1 - {month.strftime('%d %b %Y')}" for month in MONTH_LIST],label_visibility='collapsed')
            selectedMonth = selectedMonth.split(' - ')[1].replace(" ","-")


        df['Key'] = pd.to_datetime(df['Key'])

        df = df.where(df['Key'] <= datetime.strptime(selectedMonth,'%d-%b-%Y')).where(df['Key'] >= datetime.strptime('1'+selectedMonth[2:],'%d-%b-%Y')).dropna().sort_values('Key')
        df['Key'] =  df['Key'].apply(str)
        df['Amount'] = to_float(df['Amount'])
        df = df.set_index('Key')
        with cols[0]:
            st.dataframe(df,use_container_width=True,height=1000,hide_index=True)
        with cols[1]:
            st.write('')
            st.subheader(f"Total Spends : {round(df.where(df['Type'] == 'Debit')['Amount'].sum(axis=0, skipna=True),2)} Rs.")

    with tabs[1]:
        df = pd.DataFrame(data,columns=DF_COLUMNS)

        nav_cols = st.columns([0.125,0.125,0.125,0.125,0.25,0.125,0.125])

        with nav_cols[0]:

            selectedMonth = st.date_input(label="Date",label_visibility='collapsed',value=(MONTH_LIST[0].replace(day=1),MONTH_LIST[0]),min_value=MONTH_LIST[-1].replace(day=1),max_value=MONTH_LIST[0])
            # selectedMonth = st.selectbox("month", [f"1 - {month.strftime('%d %b %Y')}" for month in MONTH_LIST],
            #                              label_visibility='collapsed')

            startMonth, endMonth = selectedMonth[0], selectedMonth[1]

        # Filter DF based on Selected Date
        df['Key'] = pd.to_datetime(df['Key'])
        df = df.where(df['Key'].dt.date <= endMonth).where(
            df['Key'].dt.date >= startMonth).dropna().sort_values('Key')
        df['Key'] = df['Key'].apply(str)

        df = df.set_index('Key')

        # If any unsaved-changes are in Session, merge them with old data
        if st.session_state['DF_UPDATES'] is not None:
            df.update(st.session_state['DF_UPDATES'])
            df['Tags'] = df['Tags'].apply(tuple)
            st.session_state['DF_UPDATES']['Tags'] = st.session_state['DF_UPDATES']['Tags'].apply(tuple)
            df = pd.concat([df, st.session_state['DF_UPDATES']], axis='index')
            df['Tags'] = df['Tags'].apply(list)
            st.session_state['DF_UPDATES']['Tags'] = st.session_state['DF_UPDATES']['Tags'].apply(list)

        # remove , from amount
        df['Amount'] = to_float(df['Amount'])

        # Filter DF based on Deleted Tags
        lst = []
        dct = df['Tags'].to_dict()
        for x in dct:
            if 'Deleted' not in dct[x]:
                lst.append(x)
        df = df.loc[lst]

        with nav_cols[1]:
            mode = st.selectbox("mode",placeholder="Choose Payment Method", options=df['Mode'].drop_duplicates().to_list(), label_visibility='collapsed',index=None)
            if mode:
                df = df.where(df['Mode'] == mode).dropna()
                st.write(df['Mode'] == mode)
        with nav_cols[2]:
            acc = st.selectbox('X', placeholder="Choose an Account to Filter", key="ACC", options=['All']+list(set([x.split('(')[1].split(')')[0].strip() for x in df['Account'].to_list()])) + list(set([x.split('(')[0].strip() for x in df['Account'].to_list()]))
                         , label_visibility='collapsed',index=None)
            if acc:
                df = df.where(df['Account'].str.contains(acc.strip())).dropna()

        with nav_cols[3]:
            type = st.selectbox("spend_type", placeholder="Choose Payment Type" , options= df['Type'].drop_duplicates().to_list(), index=None, label_visibility='collapsed')
            if type:
                df = df.where(df['Type'] == type).dropna()

        with nav_cols[4]:
            tags = st.multiselect("X", options= list(set(','.join([ ','.join(x) for x in df['Tags'].drop_duplicates().to_list()]).split(','))),
                                  label_visibility='collapsed')
            if tags:
                lst = []
                dct = df['Tags'].to_dict()
                for x in dct:
                    if set(tags).intersection(dct[x]):
                        lst.append(x)
                df = df.loc[lst]



        cols = st.columns([0.75,0.25],gap='medium')

        with cols[0]:
            if st.session_state['TAGS_EDITABLE']:
                df['Tags'] = df['Tags'].apply(' , '.join)
                df['Split'] = False
                st.session_state['COL_CONFIG'] = {
                    "Tags": st.column_config.TextColumn(
                        "Tags",
                        help="Tags to identify the transaction",
                        width="medium",
                    ),
                    "Split" : st.column_config.CheckboxColumn(
                        "Split Transaction"
                    )
                }
            else :

                st.session_state['COL_CONFIG'] = {
                    "Tags": st.column_config.ListColumn(
                        "Tags",
                        help="Tags to identify the transaction",
                        width="medium",

                    )
                }

            # Final Filters
            df = df.reset_index()
            df['Key'] = df['Key'].apply(str)
            df = df.drop_duplicates(subset=['Key'])
            df = df.set_index('Key')
            df = df.sort_values(axis=0,by=df.index.name,ascending=False)

            changes = st.data_editor(df,
                           key='DETAILED_EDITOR',
                           use_container_width=True,
                           hide_index=True,
                           disabled=not st.session_state['TAGS_EDITABLE'],
                           height=1000,
                           column_config=st.session_state['COL_CONFIG']  )

        with nav_cols[6]:
            if not st.session_state['TAGS_EDITABLE']:
                st.button('Edit Data', key='Edit_BTN',use_container_width=True)
            else:
                st.button('Save', key='Save_BTN',use_container_width=True,on_click=save_df,args=(df, changes))

        with nav_cols[5]:

            merge_shown = False
            if st.session_state['TAGS_EDITABLE'] and (True in ([False] if 'Split' not in changes.columns else changes['Split'].to_list())):
                selected = changes.where(changes['Split'] == True).dropna()
                selected['Tags'] = selected['Tags'].apply(lambda x: x.split(' , '))
                selected = selected.reset_index()
                selected = selected.to_dict()
                showMerge, tgt_key, crrnt_key = False, None, None
                for x in selected['Key']:
                    key = selected['Key'][x]
                    if 'Split' in selected['Tags'][x] and len(selected['Key']) == 2:
                        if showMerge:
                            tgt_key = None
                            showMerge = False
                        else:
                            showMerge = True
                            crrnt_key = key
                        bnk, acc = selected['Account'][x].split(' ')
                        acc = acc.split('(')[1].split(')')[0]
                        src = paymentInfo[bnk][acc][key]['refNo']
                    elif selected['Type'][x] == 'Credit' and len(selected['Key']) == 2:
                        tgt_key = key

                if showMerge and tgt_key and crrnt_key:
                    merge_shown = True
                    st.button('Merge Dues', key='merge_BTN', use_container_width=True,
                              on_click=merge_dues, args=(src, tgt_key, crrnt_key, changes))

            if not merge_shown and st.session_state['TAGS_EDITABLE'] and (True in ([False] if 'Split' not in changes.columns else changes['Split'].to_list())):
                st.button('Split Selected Transactions', key='Split_BTN',use_container_width=True,on_click=check_split,args=(df,changes))

        with cols[1]:

            # Filter DF based on Ignore Tags
            lst = []
            dct = df['Tags'].to_dict()
            for x in dct:
                if 'Ignore' not in dct[x]:
                    lst.append(x)
            df = df.loc[lst]


            st.subheader(f" **Total Spends :** Rs {math.floor(df[df['Type'] == 'Debit']['Amount'].sum())} /-")
            st.subheader(f" **Total Gains :** Rs {math.floor(df[df['Type'] == 'Credit']['Amount'].sum())} /-")
            st.subheader(f" **Total Dues :** Rs {math.floor(df[df['Type'] == 'FutureCredit']['Amount'].sum())} /-")
            st.subheader(f" **Selected Sum :** Rs 0 /-")
            if type == 'FutureCredit':
                st.dataframe(
                    df.groupby('From/To').agg(
                        Due=('Amount', 'sum'),
                        Count=('Amount', 'count')
                    )
                )