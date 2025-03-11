from pandas import DataFrame
import pandas as pd
import glob
import os
pd.options.display.max_columns = None


########### 当月の1日を指定 ###########
this_month = pd.to_datetime("2025/3/1")
#####################################

flp = "\\\\sample\\moto\\"
flp2 = "\\\\sample\\開通データ\\開通\\"

## トレイルデータ加工
df_games = pd.read_csv(flp+ "applications.csv",encoding="cp932")
df_games = df_games.loc[:,["po_id","agency_application_date","arrival_date","status","agency_id","user_application_code","user_course_name","application_option_name_1","application_option_name_2","payment_method","hikari_diversion_consent_number"]]


df_games.loc[df_games["payment_method"] == 1, "payment_method"] = "クレジットカード"
df_games.loc[df_games["payment_method"] == 2, "payment_method"] = "未登録(口座振替)"

df_games["agency_application_date"] = pd.to_datetime(df_games["agency_application_date"], errors='coerce')
df_games["arrival_date"] = pd.to_datetime(df_games["arrival_date"], errors='coerce')
# df_games["elapsed_months"] = (df_games["arrival_date"].dt.year - df_games["agency_application_date"].dt.year) * 12 + (df_games["arrival_date"].dt.month - df_games["agency_application_date"].dt.month)

df_games["agency_application_date"]  = df_games["agency_application_date"].fillna("1900-01-01")
df_games["arrival_date"]  = df_games["arrival_date"].fillna("1900-01-01")

df_games = df_games[(df_games["agency_application_date"] < this_month) & (df_games["arrival_date"] < this_month)]


df_games['hikari_diversion_consent_number'] = df_games['hikari_diversion_consent_number'].fillna('新規')
df_games.loc[df_games['hikari_diversion_consent_number'] != '新規', 'hikari_diversion_consent_number'] = '転用'
df_games["po_id"] = df_games["po_id"].fillna(0)
df_games = df_games.fillna("-")

# df_games['course_name'] = df_games['user_course_name'] + ' ' + df_games['application_option_name_1'] + ' ' + df_games['application_option_name_2']	
df_games['course_name'] = df_games['user_course_name'] + ' ' + df_games['application_option_name_1']
df_games = df_games.rename(columns={'po_id':'P_ID'})
df_games = df_games.rename(columns={'agency_application_date':'申込日'})
print(df_games)

# df_games.to_csv(flp + "sample集計データ.csv",encoding="cp932",index=False)



## 開通データを加工
kijun_date = "20220801"

csv_files = [file for file in glob.glob(os.path.join(flp2, "*.csv"))if os.path.basename(file)[:8].isdigit() and os.path.basename(file)[:8] >= kijun_date and os.path.getsize(file) > 0]
df_kaituu = pd.concat([pd.read_csv(file, encoding='cp932') for file in csv_files], ignore_index=True)
print(df_kaituu["P_ID"].dtype)  

df_kaituu = df_kaituu.drop_duplicates()
df_kaituu = df_kaituu.loc[:,["P_ID","申込日","開通日","オプション名コース名"]]
df_kaituu = df_kaituu[df_kaituu['オプション名コース名'].str.contains("Games", case=False, na=False)]
df_kaituu = df_kaituu.drop_duplicates(subset=["P_ID","申込日"])
df_kaituu = df_kaituu.reset_index(drop=True)

df_kaituu["申込日"] = pd.to_datetime(df_kaituu["申込日"], errors='coerce')
df_kaituu["開通日"] = pd.to_datetime(df_kaituu["開通日"], errors='coerce')
df_kaituu = df_kaituu[(df_kaituu["申込日"] < this_month) & (df_kaituu["開通日"] < this_month)]
df_kaituu["経過月"] = (df_kaituu["開通日"].dt.year - df_kaituu["申込日"].dt.year) * 12 + (df_kaituu["開通日"].dt.month - df_kaituu["申込日"].dt.month)

df_games["P_ID"] = pd.to_numeric(df_games["P_ID"], errors="coerce").astype("Int64")
df_kaituu["P_ID"] = pd.to_numeric(df_kaituu["P_ID"], errors="coerce").astype("Int64")
print(df_kaituu)


df_merge = pd.merge(df_games, df_kaituu, on=["P_ID","申込日"], how="left")
df_merge["開通日"] = df_merge["開通日"].fillna(df_merge["arrival_date"])
df_merge = df_merge.fillna("-")

df_merge.to_csv(flp + "集計データ.csv",encoding="cp932",index=False)