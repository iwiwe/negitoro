## 解約者の通信状況から当月に解約になりそうなIDをピックアップし、販路別に解約アラートリストを作成し解約抑止に役立てる試み。
## 解約当月の通信量が、解約前月と前々月から一定量落ち込む傾向を把握し、解約当月パケットの落ち率を継続ユーザーのパケットに当て込み。
## 直近３ヶ月以上継続しているユーザーのみを抽出（ある程度のパケット傾向を把握するため）
## 0GBが連続しているユーザーはデータから除外（休眠ユーザーを刺激すると解約に繋がるため）

## 前々月以前のフォルダには、アラートリストにピックアップされたユーザーが前月に実際に解約したかどうかを確認するため、解約結果を付与し検証。
## 解約結果は会社別と、全社の合算[yymm_total_result.csv]にて抽出
## 通常の保有に対する解約率は2%前後だが、アラートリストからの解約率は平均6％以上のためリストの精度は高いことが分かる。


import pandas as pd
from pandas import DataFrame
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
pd.options.display.max_columns = None

flp = '\\\\sample\\moto\\'
flp2 ="\\\\sample\\12.kakou_packet\\01.packet_ID\\"

today = datetime.today()

month_1 = (today + relativedelta(months=-1)).strftime('%Y%m')[2:] ####先月
month_2 = (today + relativedelta(months=-2)).strftime('%Y%m')[2:] ####先々月	
month_3 = (today + relativedelta(months=-3)).strftime('%Y%m')[2:] ####三ヶ月前
months_list = [month_3, month_2, month_1]
print(months_list)


df = pd.read_csv(flp +"packet元\\WiFi.csv",encoding="cp932")


for i in months_list:
	df_pa=pd.read_csv(flp2 +'packet_ID_' + i + '.csv',encoding="cp932")	
	df_pa=df_pa.loc[:,['ID','パケット_GB']]
	df=pd.merge(df,df_pa,on='ID',how='left')
	df['パケット_GB'] = df['パケット_GB'].round(3)
	df=df.rename(columns={'パケット_GB':i +'_GB'})

df=df.fillna(0)
df.loc[df.iloc[:,8]!=0, 'アラートx_%'] = df.iloc[:, 10] / df.iloc[:, 8]*100
df.loc[df.iloc[:,9]!=0, 'アラートy_%'] = df.iloc[:, 10] / df.iloc[:, 9]*100

df = df[(df['アラートx_%'] >= 0) & (df['アラートx_%'] < 33)]
df = df[(df['アラートy_%'] >= 0) & (df['アラートy_%'] < 40)]
df['アラートx_%'] = df['アラートx_%'].round(1)
df['アラートy_%'] = df['アラートy_%'].round(1)
# df = df[df['アラートx_%'] <= df['アラートy_%']]
print(df)


####会社リストの作成
df_DC_list = df['会社名'].drop_duplicates()
list_name = list(map(str,df_DC_list))
print(list_name)

for j in list_name:
	df_DC = df[df['会社名'] == j]
	df_DC.to_csv(flp + 'packet_alert\\'+ month_1 +'packet_alert_' + j + '.csv', encoding='cp932', index = False)
	print(j +"完了")



##解約結果の当て込み
dir_path ='\\\\sample\\packet_alert\\'+ month_2 +'\\'
files_file = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]

list_past = pd.DataFrame(data=files_file )
list_past = list_past[list_past[0] != month_2 + '_total_result.csv']
list_past = list_past.replace({'.csv': '',month_2+'packet_alert_':''}, regex=True)
print(list_past)

df_past = pd.read_csv(flp+"元\\kaiyaku.csv",encoding="cp932")
df_past = df_past.rename(columns={'解約年月': '解約年月（実績）'})

df_total = pd.DataFrame()

for k in list_past[0]:
	df_kaiyaku = pd.read_csv(flp+'packet_alert\\'+ month_2 +'\\'+ month_2 +'packet_alert_' + k + '.csv',encoding="cp932")
	# df_kaiyaku = df_kaiyaku.drop(['解約年月（実績）'], axis=1)
	df_kaiyaku = pd.merge(df_kaiyaku,df_past,on='ID',how='left')
	df_kaiyaku.to_csv(flp+'packet_alert\\' + month_2 + '\\' + month_2 + 'packet_alert_' + k + '.csv', encoding='cp932', index = False)
	df_total = df_total.append(df_kaiyaku, ignore_index=True)
	print(k+"完了")
df_total.to_csv(flp+'packet_alert\\'+ month_2 +'\\'+ month_2 +'_total_result.csv', encoding='cp932', index = False)