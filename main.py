
from UI import *
import json


# Selected Sum
# Credit period filters
from streamlit_cookies_controller import CookieController

st.set_page_config(
    page_title="Data Explorer",
    layout="wide"
)

updates = False
cookies = CookieController()
with open('info.json','r') as f:
    data = json.load(f)
    # URL = "https://python-api-finance-dashboards.onrender.com/records?uname=ritariya&key=210102"
    URL = "https://finance---api.vercel.app/records?uname=ritariya&key=210102"
    # URL = "http://127.0.0.1:5000/records?uname=ritariya&key=210102"
    if cookies.get('finance-user') is None:
        x = st.selectbox(label='Enter you Name : ',options=['Ritam','Riya'],index=None)
        if x:
            cookies.set('finance-user',x)
            st.rerun()

    user = cookies.get('finance-user')
    st.write(user)
    if user:
        if user not in data:
            updates = True
            paymentInfo = requests.get(URL,headers={'USER':user}).json()
            data[user] = {
                'LastUpdateDate' : str(datetime.now().strftime("%d-%b-%Y %p")),
                'data' :  paymentInfo
            }
        elif datetime.strptime(data[user]['LastUpdateDate'],"%d-%b-%Y %p").month != datetime.now().month or (
                datetime.strptime(data[user]['LastUpdateDate'],"%d-%b-%Y %p").day != datetime.now().day) or (
                datetime.strptime(data[user]['LastUpdateDate'], "%d-%b-%Y %p").day == datetime.now().day and
                data[user]['LastUpdateDate'][-2] != datetime.now().strftime('%p')[-2]
        ) or cookies.get('reload') == True:

            cookies.remove('reload')
            updates = True
            paymentInfo = requests.get(URL,headers={'USER':user}).json()
            data[user]['LastUpdateDate'] = str(datetime.now().strftime("%d-%b-%Y %p"))
            data[user]['data'] = paymentInfo

        paymentInfo = data[user]['data']
    else:
        paymentInfo = {}

if updates:
    with open('info.json','w') as outfile:
        json.dump(data, outfile)

if user:
    generate_basic_ui(user, paymentInfo)



