import pandas as pd
from pandas import DataFrame
import os
import glob
import datetime

pd.options.display.max_columns = None

start_date = datetime.date(2023, 12, 19)

####################変更する##############
end_date = datetime.date(2025, 2, 28) ###
#########################################


flp = '\\\\sample\\03.packet_daily\\'
flp1 = '\\\\sample\\moto\\'
delta = datetime.timedelta(days=1)

list_of_files = glob.glob(flp+'*.csv')

df_PK = pd.DataFrame(index=[],columns=[])
for i in list_of_files:
	df = pd.read_csv(i,encoding="cp932")
	df_PK = df_PK.append(df)


yyyy_mm_dd = start_date.strftime('%Y%m%d')
df_PK = df_PK.loc[:,["回線ID","通信日","通信量(GB)"]]
df_PK = df_PK.sort_values(['通信日'])
df_PK = df_PK.drop_duplicates(subset=["回線ID","通信日","通信量(GB)"],keep='first')
print(df_PK)


df_moto = pd.read_csv(flp1+"PRmoto.csv",encoding="cp932")
df_shinki = df_moto[df_moto['登録種別【変換】'] == "新規プリペイド"]
df_shinki = df_shinki[df_shinki['プリペイド利用可能日'] != ""]
df_shinki = df_shinki.loc[:,["簡易会社名","回線ID","プリペイドプランコード","プラン名称","プリペイド容量","プリペイド日数",]]

df_NEW_all = pd.read_csv(flp1+"report_all.csv",encoding="cp932",usecols=[2, 12, 20],names = ['回線ID', '利用開始日', '終了日'])
df_shinki = pd.merge(df_shinki,df_NEW_all,on=['回線ID'],how='left').fillna("-")
df_shinki = df_shinki[df_shinki['利用開始日'] != "-"]
print(df_shinki)

df_shinki['利用開始日'] = df_shinki['利用開始日'].astype(str).str.split('.').str[0]
df_shinki['利用開始日'] = pd.to_datetime(df_shinki['利用開始日'], format='%Y%m%d')
df_shinki['利用開始日'] = df_shinki['利用開始日'].dt.date
df_shinki['終了日'] = df_shinki['終了日'].astype(str).str.split('.').str[0]
df_shinki['終了日'] = pd.to_datetime(df_shinki['終了日'], format='%Y%m%d')
df_shinki['終了日'] = df_shinki['終了日'].dt.date
df_mikanryo = df_shinki[df_shinki['終了日'] > end_date]
df_shinki = df_shinki[df_shinki['終了日'] <= end_date]
df_mikanryo.to_csv(flp1+"未完了_moto.csv",encoding="cp932",index=False)


while start_date <= end_date:
	yyyy_mm_dd = start_date.strftime('%Y%m%d')
	df_PK['通信日'] = df_PK['通信日'].astype(str)
	df_PK1 = df_PK[df_PK['通信日'] == yyyy_mm_dd]
	df_PK1 = df_PK1.loc[:,["回線ID","通信量(GB)"]]
	print(yyyy_mm_dd)
	df_shinki = pd.merge(df_shinki, df_PK1, on='回線ID', how='left').fillna(0)
	date = pd.to_datetime(yyyy_mm_dd, format='%Y%m%d')
	df_shinki = df_shinki.rename(columns={'通信量(GB)': date})
	start_date += delta 


df_shinki['合計_GB'] = 0
df_shinki['平均_GB'] = 0
df_shinki['全期間合計_GB'] = 0
df_shinki['容量超過'] = "-"

cols = list(df_shinki.columns)
cols.remove('終了日')
cols.remove('合計_GB')
cols.remove('平均_GB')
cols.remove('全期間合計_GB')
cols.remove('容量超過')
df_index = cols.index('利用開始日')
cols.insert(df_index+1, '終了日')
cols.insert(df_index+2, '合計_GB')
cols.insert(df_index+3, '平均_GB')
cols.insert(df_index+4, '全期間合計_GB')
cols.insert(df_index+5, '容量超過')

df_shinki = df_shinki[cols]


df_shinki['利用開始日'] = pd.to_datetime(df_shinki['利用開始日'], format='%Y/%m/%d')
df_shinki['終了日'] = pd.to_datetime(df_shinki['終了日'], format='%Y/%m/%d')

df_shinki['合計_GB'] = df_shinki.apply(lambda row: row.iloc[12:][(pd.to_datetime(row.index[12:], format='%Y/%m/%d') >= \
row['利用開始日']) & (pd.to_datetime(row.index[12:], format='%Y/%m/%d') <= row['終了日'])].sum(), axis=1)

df_shinki.loc[df_shinki['合計_GB']>df_shinki['プリペイド容量'], '容量超過'] = 'over'
df_shinki.loc[df_shinki['合計_GB']>df_shinki['プリペイド容量'], '合計_GB'] = df_shinki['プリペイド容量']  
df_shinki['平均_GB'] = df_shinki['合計_GB'] / (df_shinki['プリペイド日数'] )
df_shinki['全期間合計_GB'] = df_shinki.iloc[:, 12:].sum(axis=1)


df_tsuika = df_moto[df_moto['登録種別【変換】'] == "追加プリペイド"]
df_tsuika['追加履歴'] = "追加" 
df_tsuika = df_tsuika.drop_duplicates(subset=["回線ID"],keep='first')
df_tsuika = df_tsuika.loc[:,["回線ID","追加履歴"]]


df_mrg = pd.merge(df_shinki,df_tsuika,on=['回線ID'],how='left').fillna("-")

cols = df_mrg.columns.tolist()
cols.insert(12, cols.pop(cols.index('追加履歴')))
df_mrg = df_mrg[cols]

df_mrg.to_csv(flp1+"新規_moto.csv",encoding="cp932",index=False)



##利用開始日をNとしたデータを作成
new_df = pd.DataFrame()
date_columns = [col for col in df_mrg.columns if col not in\
 ['簡易会社名', '回線ID', 'プリペイドプランコード', 'プラン名称', 'プリペイド容量', 'プリペイド日数', '利用開始日', '終了日', '合計_GB', '平均_GB', '全期間合計_GB', '容量超過', '追加履歴']]

for idx, row in df_mrg.iterrows():
	start_date = row['利用開始日']
	end_date = row['終了日']

	valid_dates = [date for date in date_columns if start_date <= date <= end_date]
	numeric_dates = [(pd.to_datetime(date) - pd.to_datetime(start_date)).days for date in valid_dates]

	new_row = row[['簡易会社名', '回線ID', 'プリペイドプランコード', 'プラン名称', 'プリペイド容量', 'プリペイド日数', '利用開始日', '終了日', '合計_GB', '平均_GB', '全期間合計_GB', '容量超過', '追加履歴']]

	for numeric_date in numeric_dates:
		original_date = start_date + pd.DateOffset(days=numeric_date) 
		if not pd.isna(row[original_date]):
			new_row[str(numeric_date)] = row[original_date]
	new_df = new_df.append(new_row)

	print(new_row)
new_df.to_csv(flp1 + "新規_N日moto.csv", encoding='cp932', index=False)
