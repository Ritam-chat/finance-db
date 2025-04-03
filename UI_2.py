import calendar
import math
from datetime import datetime, date
import streamlit as st
import pandas as pd

from utils import to_float, set_cookies, save_df, check_split, concat_datas, filter_date, new_trans, merge_details, \
    merge_dues
from streamlit_ace import st_ace

# Default
DF_COLUMNS = ['Key','Account','Date','From/To','Amount','Mode','Type','Tags']
MONTH_LIST = []
TAB_LIST = ['Monthly Summary','Detailed Summary']
CURR_MONTH, CURR_YEAR = datetime.now().month, datetime.now().year

for x in range(5):
    if CURR_MONTH < 1:
        CURR_YEAR-=1
        CURR_MONTH = 12
    _,last = calendar.monthrange(CURR_YEAR,CURR_MONTH)
    MONTH_LIST.append(date(CURR_YEAR,CURR_MONTH,last))
    CURR_MONTH-=1






def generate_base_details(data):

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

def generate_detailed_ui(data,more):

    df = pd.DataFrame(data, columns=DF_COLUMNS)

    # Mandatory Operations
    # Remove ',' from amount
    df['Amount'] = to_float(df['Amount'])
    # Remove Deleted Transactions
    dct, lst = df['Tags'].to_dict(), []
    for x in dct:
        if 'Deleted' not in dct[x]:
            lst.append(x)
    df = df.loc[lst]

    nav_cols = st.columns([0.125, 0.125, 0.125, 0.125, 0.25, 0.125, 0.125])

    # Date Input
    with nav_cols[0]:
        selectedMonth = st.date_input(label="Date", label_visibility='collapsed',
                                      value=(MONTH_LIST[0].replace(day=1), MONTH_LIST[0]),
                                      min_value=MONTH_LIST[-1].replace(day=1), max_value=MONTH_LIST[0])
        try:
            startMonth, endMonth = selectedMonth[0], selectedMonth[1]
        except:
            startMonth, endMonth = selectedMonth[0], MONTH_LIST[0]

    # Payment Method
    with nav_cols[1]:
        mode = st.selectbox("mode", placeholder="Choose Payment Method", options=df['Mode'].drop_duplicates().to_list(),
                            label_visibility='collapsed', index=None)
        if mode:
            df = df.where(df['Mode'] == mode).dropna()

    # Account No
    with nav_cols[2]:
        acc = st.selectbox('X', placeholder="Choose an Account to Filter", key="ACC", options=['All'] + list(
            set([x.split('(')[1].split(')')[0].strip() for x in df['Account'].to_list()])) + list(
            set([x.split('(')[0].strip() for x in df['Account'].to_list()]))
                           , label_visibility='collapsed', index=None)
        if acc:
            df = df.where(df['Account'].str.contains(acc.strip())).dropna()

    # Payment Type
    with nav_cols[3]:
        type = st.selectbox("spend_type", placeholder="Choose Payment Type",
                            options=df['Type'].drop_duplicates().to_list(), index=None, label_visibility='collapsed')
        if type:
            df = df.where(df['Type'] == type).dropna()

    # Tags
    with nav_cols[4]:
        tags = st.multiselect("X", options=list(
            set(','.join([','.join(x) for x in df['Tags'].drop_duplicates().to_list()]).split(','))),
                              label_visibility='collapsed')
        if tags:
            lst = []
            dct = df['Tags'].to_dict()
            for x in dct:
                if set(tags).intersection(dct[x]):
                    lst.append(x)
            df = df.loc[lst]


    df = df.set_index('Key')
    data = df.to_dict()


    # Sort Based on Date
    filtered_keys = []
    for key in data['Account']:
        date_filter = endMonth >= pd.to_datetime(key).date() >= startMonth
        # st.write(date_filter)
        if not date_filter:
            filtered_keys.append(key)

    data = filter_date(data, filtered_keys)

    if st.session_state['DF_UPDATES'] is not None:
        updates = st.session_state['DF_UPDATES'].to_dict()
        data = concat_datas(data, updates)

    more_cols = st.columns([0.125, 0.125, 0.125, 0.125, 0.25, 0.125, 0.125])

    if more:
        pass
    # Will implement later
    #     with more_cols[1]:
    #         mode = st.selectbox("modke", placeholder="Choose Payment Method",
    #                             options=df['Mode'].drop_duplicates().to_list(),
    #                             label_visibility='collapsed', index=None)
    #
    # else:
    #     pass


    df = pd.DataFrame(data)

    # Show DataFrame
    cols = st.columns([0.75, 0.25], gap='medium')

    with cols[0]:
        if st.session_state['TAGS_EDITABLE']:
            df['Tags'] = df['Tags'].apply(','.join)
            df['Split'] = False
            st.session_state['COL_CONFIG'] = {
                "Tags": st.column_config.TextColumn(
                    "Tags",
                    help="Tags to identify the transaction",
                    width="medium",
                ),
                "Split": st.column_config.CheckboxColumn(
                    "Split Transaction"
                )
            }
        else:

            st.session_state['COL_CONFIG'] = {
                "Tags": st.column_config.ListColumn(
                    "Tags",
                    help="Tags to identify the transaction",
                    width="medium",

                )
            }

        # Final Filters

        df = df.sort_index(ascending=False)

        changes = st.data_editor(df,
                                 key='DETAILED_EDITOR',
                                 use_container_width=True,
                                 hide_index=True,
                                 disabled=not st.session_state['TAGS_EDITABLE'],
                                 height=1000,
                                 column_config=st.session_state['COL_CONFIG'])

        # st.write(changes)
        # st.write(st.session_state['DETAILED_EDITOR'])

    with cols[1]:

        if more:
            cols = st.columns([1])

            if st.session_state['TAGS_EDITABLE']:
                cols = st.columns([1, 1])
                with cols[1]:
                        with st.popover('New Memo',use_container_width=True):
                            st.session_state['txt'] = ''
                            name = st.text_input('name',value=st.session_state['txt'], placeholder='Memo Title', label_visibility='collapsed')
                            if st.button('Create'):
                                st.session_state['MEMOS'][name] = ''
                                st.session_state['txt'] = ''

            keys = list(st.session_state['MEMOS'].keys())
            with cols[0]:
                selected_memo = st.selectbox('Memos : ', keys, label_visibility='collapsed')

            text = st.session_state['MEMOS'].get(selected_memo,'')

            # new_text = st.text_area('Memo for You : ', value=text, height=500, key='memo',
            #                         disabled=not st.session_state['TAGS_EDITABLE'])
            if selected_memo is not None:
                new_text = st_ace(
                    placeholder="Write your memo here",
                    language='XML',
                    value=text,
                    theme='eclipse',
                    keybinding='sublime',
                    font_size=15,
                    tab_size=4,
                    show_gutter=False,
                    show_print_margin=False,
                    wrap=False,
                    auto_update=False,
                    readonly=not st.session_state['TAGS_EDITABLE'],
                    min_lines=45,
                    key="memo",
                )
            else:
                new_text = None

            if text != new_text:
                st.session_state['MEMO_KEY'] = selected_memo
            elif 'MEMO_KEY' in st.session_state:
                st.session_state.pop('MEMO_KEY')


        with nav_cols[6]:
            if not st.session_state['TAGS_EDITABLE']:
                st.button('Edit Data', key='Edit_BTN', use_container_width=True)
            else:
                st.button('Save', key='Save_BTN', use_container_width=True, on_click=save_df, args=(df, changes))

        with nav_cols[5]:
            if st.session_state['TAGS_EDITABLE']:
                with st.popover('New Transaction', use_container_width=True):
                    t_acc = st.selectbox('Account of Transaction',options=list(
            set([x for x in df['Account'].to_list()])),index=None)
                    t_date = st.date_input('Date of Transaction', format="YYYY-MM-DD",value='today')
                    t_from_to = st.text_input('Transaction User : ')
                    t_amount = st.number_input('Amount : ', max_value=10000)
                    t_mode = st.selectbox('Mode : ', options=['UPI','VPA','Split','Bank','NEFT','Withdrawal','Repayment','Card','Transaction','Refund'])
                    t_type = st.selectbox('Type : ', options=['Debit','Credit','FutureCredit'])

                    now = datetime.now()
                    now.replace(month=t_date.month, year = t_date.year, day = t_date.day)

                    enable = t_acc is not None and t_date is not None and t_from_to is not None and t_from_to != '' and t_amount is not None and t_amount != 0 and t_mode is not None and t_type is not None
                    if st.button('Create', disabled= not enable, use_container_width=True):

                        data = {
                            'Key': [now.strftime('%Y-%m-%d %H:%M:%S')],
                            'Account': [t_acc],
                            'Date': [now.strftime("%d-%b, %I:%M %p")],
                            'From/To': [t_from_to],
                            'Amount': [t_amount],
                            'Mode': [t_mode],
                            'Type': [t_type],
                            'Tags': [['New Trans']],
                        }
                        new_trans(data)
                        st.toast('New Transaction Added!')
                        st.rerun()

        if more and st.session_state['TAGS_EDITABLE']:
            with more_cols[6]:
                show, fc_index, c_index = merge_details(df, changes)
                if show:
                    st.button('Merge Dues', key='merge_BTN', use_container_width=True,
                              on_click=merge_dues, args=(fc_index, c_index, changes)
                              )

            with more_cols[5]:
                if st.session_state['TAGS_EDITABLE'] and (
                            True in ([False] if 'Split' not in changes.columns else changes['Split'].to_list())):
                    with st.popover('Split Transactions', use_container_width=True):
                        split_config = {}
                        enable = True
                        quantity = st.slider('How many splits you want ?', min_value=2, max_value=10)
                        s_type = st.selectbox('Split Type', options=['Equally', 'Percentage', 'Manual'])

                        split_config['quantity'] = quantity
                        split_config['type'] = s_type

                        if s_type == 'Percentage':
                            split_config['splits'] = []
                            total_dn = 0
                            for x in range(quantity):
                                if x != 0:
                                    us = st.text_input(f'User for Split {x} : ')
                                else:
                                    us = st.session_state['USER']
                                am = st.number_input(f'Percentage for Split {x} : ' if x != 0 else 'Your Split Percentage : ', max_value=100, min_value=0)
                                enable = enable and (us.strip() != '')
                                total_dn += am
                                split_config['splits'].append({'user':us,'amount':am})
                            if total_dn != 100:
                                st.warning('Total Percentage should be 100')
                                enable = False
                        elif s_type == 'Manual':
                            split_config['splits'] = []
                            total_dn = 0
                            for x in range(quantity):
                                if x != 0:
                                    us = st.text_input(f'User for Split {x} : ')
                                else:
                                    us = st.session_state['USER']
                                am = st.number_input(
                                    f'Amount for Split {x} : ' if x != 0 else 'Your Split Amount : ',
                                    min_value=0)
                                total_dn += am
                                enable = enable and (us.strip() != '')
                                split_config['splits'].append({'user':us,'amount':am})
                        elif s_type == 'Equally':
                            split_config['splits'] = []
                            for x in range(quantity):
                                if x != 0:
                                    us = st.text_input(f'User for Split {x+1} : ')
                                else:
                                    us = st.text_input(f'User for Split {x+1} : ',value=st.session_state['USER'], disabled=True)
                                enable = enable and (us.strip() != '')
                                split_config['splits'].append({'user':us})
                        if st.button('Split',disabled= not enable, use_container_width=True):
                            check_split(df, changes, split_config)
                            st.toast('Split Successful!')
                            st.rerun()

        # Filter DF based on Ignore Tags
        dct, lst = df['Tags'].to_dict(), []
        for x in dct:
            if 'Ignore' not in dct[x] and 'Cleared' not in dct[x]:
                lst.append(x)
        df = df.loc[lst]


    if not more:

        with cols[1]:

            with st.columns([0.5,1,0.5])[1]:
                st.markdown(f" **Total Spends :** Rs {math.floor(df[df['Type'] == 'Debit']['Amount'].sum())} /-")
                st.markdown(f" **Total Gains :** Rs {math.floor(df[df['Type'] == 'Credit']['Amount'].sum())} /-")
                st.markdown(f" **Total Dues :** Rs {math.floor(df[df['Type'] == 'FutureCredit']['Amount'].sum())} /-")
                st.markdown(f" **Selected Sum :** Rs 0 /-")

            if type == 'FutureCredit':
                st.dataframe(
                    df.groupby('From/To').agg(
                        Due=('Amount', 'sum'),
                        Count=('Amount', 'count')
                    )
                )










def generate_basic_ui(user, paymentInfo):

    st.session_state['USER'] = user

    if 'TAGS_EDITABLE' not in st.session_state:
        st.session_state['TAGS_EDITABLE'] = False
    if 'DF_UPDATES' not in st.session_state:
        st.session_state['DF_UPDATES'] = None
    if 'MEMOS' not in st.session_state:
        st.session_state['MEMOS'] = {}

    st.session_state['TAGS_EDITABLE'] = st.session_state['TAGS_EDITABLE'] if 'Edit_BTN' not in st.session_state else st.session_state['Edit_BTN']
    hd_cols = st.columns([1,0.1,0.1])
    with hd_cols[0]:
        st.header(f"Hello, {user}")
    with hd_cols[1]:
        more = st.toggle('More')
    with hd_cols[2]:
        st.button(icon="🔄",on_click=set_cookies,args=('reload',True),label=' ')

    tabs = st.tabs(TAB_LIST)
    data=[]
    for bank in paymentInfo:
        if bank == 'Stash': continue
        if bank == 'Memo' :
            st.session_state['MEMOS'] = paymentInfo[bank]
            continue
        for acc in paymentInfo[bank]:
            for key in paymentInfo[bank][acc]:
                trans = paymentInfo[bank][acc][key]
                try:
                    data.append((key, f"{bank} ({trans['account']})", trans['time'], trans['to_from'], trans['amount'],trans['mode'], trans['type'], [] if 'tags' not in trans else trans['tags']))
                except:
                    st.write(trans)

    with tabs[0]:
        generate_base_details(data)

    with tabs[1]:
        generate_detailed_ui(data,more)
