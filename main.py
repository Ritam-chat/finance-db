import requests

from UI_2 import *
import json
import time



st.set_page_config(
    page_title="Data Explorer",
    layout="wide"
)


# Selected Sum
# Credit period filters
from streamlit_cookies_controller import CookieController



updates = False
cookies = CookieController()

if cookies.getAll() == {}:
    try:
        cookies.refresh()
    except Exception as e:
        time.sleep(1)

with open('info.json','r') as f:
    data = json.load(f)
    URL = "https://finance---api.vercel.app/"
    # URL = "http://127.0.0.1:5000/records?uname=ritariya&key=210102"
    if cookies.get('finance-user') is None:
        x = st.selectbox(label='Enter you Name : ',options=['Ritam','Riya'],index=None)
        y = st.text_input(label='Enter your specific Key : ',type='password')
        if x and y:

            if requests.get(f"{URL}/auth",headers={'Username' : x,'Password':y}).status_code == 200:
                cookies.set('finance-user',x)
                st.rerun()
            else:
                st.error('Please enter correct key!')


    user = cookies.get('finance-user')

    if user:
        try:
            if user not in data:
                updates = True
                paymentInfo = requests.get(f"{URL}/records",headers={'USER':user,'Key':'210102'}).json()
                data[user] = {
                    'LastUpdateDate' : str(datetime.now().strftime("%d-%b-%Y %p")),
                    'data' :  paymentInfo
                }

            elif datetime.strptime(data[user]['LastUpdateDate'],"%d-%b-%Y %p").month != datetime.now().month or (
                    datetime.strptime(data[user]['LastUpdateDate'],"%d-%b-%Y %p").day != datetime.now().day) or (
                    datetime.strptime(data[user]['LastUpdateDate'], "%d-%b-%Y %p").day == datetime.now().day and
                    data[user]['LastUpdateDate'][-2] != datetime.now().strftime('%p')[-2]
            ) or cookies.get('reload') == True:
                if cookies.get('reload'):
                    cookies.remove('reload')
                updates = True
                paymentInfo = requests.get(f"{URL}/records",headers={'USER':user,'Key':'210102'}).json()
                data[user]['LastUpdateDate'] = str(datetime.now().strftime("%d-%b-%Y %p"))
                data[user]['data'] = paymentInfo

            paymentInfo = data[user]['data']
        except Exception as e:
            st.error('Some issue occurred : ',e)
    else:
        paymentInfo = {}

if updates:
    with open('info.json','w') as outfile:
        json.dump(data, outfile)

if user:
    generate_basic_ui(user, paymentInfo)



